# Orchestrated workflow blueprint (docs/blueprints/orchestrated-workflow.md):
#   trigger -> Step Functions state machine
#                 -> Validate (Lambda) -> Process (Lambda) -> Notify (Lambda)
# The state machine holds the process state and the retry policy per step;
# each Lambda stays stateless (docs/adr/0002-stateless-ephemeral.md).

data "archive_file" "handlers" {
  type        = "zip"
  source_dir  = "${path.module}/../../handlers"
  output_path = "${path.module}/.build/handlers.zip"
}

resource "aws_dynamodb_table" "orders" {
  name         = "orders-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "orderId"

  attribute {
    name = "orderId"
    type = "S"
  }
}

module "idempotency_table" {
  source     = "../modules/idempotency_table"
  table_name = "idempotency-keys-orchestrated-workflow-${var.environment}"
}

# One role per step, per ADR-0005 -- three separate identities, not one
# role shared across the workflow's Lambdas.
module "validate_role" {
  source              = "../modules/iam_role"
  role_name           = "orchestrated-workflow-validate-${var.environment}-role"
  assume_role_service = "lambda.amazonaws.com"
  statements = [
    {
      sid           = "ReadOrdersTable"
      actions       = ["dynamodb:GetItem"]
      resources     = [aws_dynamodb_table.orders.arn]
      justification = "Checks the order exists and its current status; never writes."
    },
    {
      sid           = "ReadWriteIdempotencyTable"
      actions       = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]
      resources     = [module.idempotency_table.table_arn]
      justification = "Reads and writes its own dedupe record, keyed on {executionId}:validate."
    },
  ]
}

module "process_role" {
  source              = "../modules/iam_role"
  role_name           = "orchestrated-workflow-process-${var.environment}-role"
  assume_role_service = "lambda.amazonaws.com"
  statements = [
    {
      sid           = "ReadWriteOrdersTable"
      actions       = ["dynamodb:GetItem", "dynamodb:UpdateItem"]
      resources     = [aws_dynamodb_table.orders.arn]
      justification = "Reads the order and transitions its status to 'refunded'."
    },
    {
      sid           = "ReadWriteIdempotencyTable"
      actions       = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]
      resources     = [module.idempotency_table.table_arn]
      justification = "Reads and writes its own dedupe record, keyed on {executionId}:process."
    },
  ]
}

module "notify_role" {
  source              = "../modules/iam_role"
  role_name           = "orchestrated-workflow-notify-${var.environment}-role"
  assume_role_service = "lambda.amazonaws.com"
  statements = [
    {
      sid           = "ReadWriteIdempotencyTable"
      actions       = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]
      resources     = [module.idempotency_table.table_arn]
      justification = "Reads and writes its own dedupe record, keyed on {executionId}:notify. Touches no other table -- this step's toy implementation sends no real notification yet."
    },
  ]
}

module "validate_function" {
  source           = "../modules/lambda_function"
  function_name    = "orchestrated-workflow-validate-${var.environment}"
  handler          = "orchestrated_workflow.handler.validate_handler"
  role_arn         = module.validate_role.role_arn
  source_zip_path  = data.archive_file.handlers.output_path
  source_code_hash = data.archive_file.handlers.output_base64sha256
  environment_variables = {
    ORDERS_TABLE_NAME      = aws_dynamodb_table.orders.name
    IDEMPOTENCY_TABLE_NAME = module.idempotency_table.table_name
  }
}

module "process_function" {
  source           = "../modules/lambda_function"
  function_name    = "orchestrated-workflow-process-${var.environment}"
  handler          = "orchestrated_workflow.handler.process_handler"
  role_arn         = module.process_role.role_arn
  source_zip_path  = data.archive_file.handlers.output_path
  source_code_hash = data.archive_file.handlers.output_base64sha256
  environment_variables = {
    ORDERS_TABLE_NAME      = aws_dynamodb_table.orders.name
    IDEMPOTENCY_TABLE_NAME = module.idempotency_table.table_name
  }
}

module "notify_function" {
  source           = "../modules/lambda_function"
  function_name    = "orchestrated-workflow-notify-${var.environment}"
  handler          = "orchestrated_workflow.handler.notify_handler"
  role_arn         = module.notify_role.role_arn
  source_zip_path  = data.archive_file.handlers.output_path
  source_code_hash = data.archive_file.handlers.output_base64sha256
  environment_variables = {
    IDEMPOTENCY_TABLE_NAME = module.idempotency_table.table_name
  }
}

module "state_machine_role" {
  source              = "../modules/iam_role"
  role_name           = "orchestrated-workflow-${var.environment}-role"
  assume_role_service = "states.amazonaws.com"
  statements = [
    {
      sid     = "InvokeWorkflowSteps"
      actions = ["lambda:InvokeFunction"]
      resources = [
        module.validate_function.function_arn,
        module.process_function.function_arn,
        module.notify_function.function_arn,
      ]
      justification = "The state machine's own least-privilege role: invoke exactly the three Lambdas this workflow orchestrates, nothing else (iam-role-convention.md's 'fields that do not apply' note)."
    },
  ]
}

# Each step retries per ADR-0003: a step can be retried by the machine, so
# each step's action is idempotent (idempotency-convention.md's
# {executionId}:{stepName} key is what makes that safe).
resource "aws_sfn_state_machine" "refund_workflow" {
  name     = "refund-workflow-${var.environment}"
  role_arn = module.state_machine_role.role_arn

  definition = jsonencode({
    Comment = "Validate, process, and notify on a refund request -- docs/blueprints/orchestrated-workflow.md"
    StartAt = "Validate"
    States = {
      Validate = {
        Type     = "Task"
        Resource = module.validate_function.function_arn
        Retry    = [{ ErrorEquals = ["States.ALL"], IntervalSeconds = 2, MaxAttempts = 2, BackoffRate = 2 }]
        Next     = "Process"
      }
      Process = {
        Type     = "Task"
        Resource = module.process_function.function_arn
        Retry    = [{ ErrorEquals = ["States.ALL"], IntervalSeconds = 2, MaxAttempts = 2, BackoffRate = 2 }]
        Next     = "Notify"
      }
      Notify = {
        Type     = "Task"
        Resource = module.notify_function.function_arn
        Retry    = [{ ErrorEquals = ["States.ALL"], IntervalSeconds = 2, MaxAttempts = 2, BackoffRate = 2 }]
        End      = true
      }
    }
  })
}
