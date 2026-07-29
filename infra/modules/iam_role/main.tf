# docs/contracts/iam-role-convention.md, made runnable: one role, every
# statement resource-scoped and action-scoped, Effect always Allow (a Deny
# here suggests the Allow set is already too broad -- narrow that instead,
# per the convention doc).

data "aws_iam_policy_document" "assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = [var.assume_role_service]
    }
  }
}

resource "aws_iam_role" "this" {
  name               = var.role_name
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
  tags               = var.tags
}

data "aws_iam_policy_document" "this" {
  dynamic "statement" {
    for_each = var.statements
    content {
      sid       = statement.value.sid
      effect    = "Allow"
      actions   = statement.value.actions
      resources = statement.value.resources
    }
  }
}

resource "aws_iam_role_policy" "this" {
  name   = "${var.role_name}-policy"
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.this.json
}

# CloudWatch Logs is the one universal grant every Lambda-assumed role
# needs regardless of the function's business logic -- least privilege
# still applies: scoped to this function's own log group, not
# logs:PutLogEvents on "*".
resource "aws_iam_role_policy" "logs" {
  count = var.assume_role_service == "lambda.amazonaws.com" ? 1 : 0
  name  = "${var.role_name}-logs"
  role  = aws_iam_role.this.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "WriteOwnLogGroup"
      Effect   = "Allow"
      Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "arn:aws:logs:*:*:log-group:/aws/lambda/${var.role_name}*"
    }]
  })
}
