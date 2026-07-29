# Synchronous API blueprint (docs/blueprints/synchronous-api.md):
#   client -> API Gateway -> Lambda -> orders table
# One deployment package for the whole handlers/ tree, shared across every
# blueprint's Lambda(s) -- they differ only in the `handler` entrypoint
# selected within it. See infra/README.md.

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
  table_name = "idempotency-keys-synchronous-api-${var.environment}"
}

module "function_role" {
  source              = "../modules/iam_role"
  role_name           = "synchronous-api-handler-${var.environment}-role"
  assume_role_service = "lambda.amazonaws.com"
  statements = [
    {
      sid           = "ReadWriteOrdersTable"
      actions       = ["dynamodb:GetItem", "dynamodb:UpdateItem"]
      resources     = [aws_dynamodb_table.orders.arn]
      justification = "Reads order state for GET, and transitions status to 'refunded' for POST /refund."
    },
    {
      sid           = "ReadWriteIdempotencyTable"
      actions       = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]
      resources     = [module.idempotency_table.table_arn]
      justification = "Reads and writes its own dedupe records per idempotency-convention.md."
    },
  ]
}

module "function" {
  source           = "../modules/lambda_function"
  function_name    = "synchronous-api-handler-${var.environment}"
  handler          = "synchronous_api.handler.lambda_handler"
  role_arn         = module.function_role.role_arn
  source_zip_path  = data.archive_file.handlers.output_path
  source_code_hash = data.archive_file.handlers.output_base64sha256

  environment_variables = {
    ORDERS_TABLE_NAME      = aws_dynamodb_table.orders.name
    IDEMPOTENCY_TABLE_NAME = module.idempotency_table.table_name
  }

  # docs/adr/0004-cold-start-and-concurrency.md: this is the blueprint
  # where provisioned concurrency most often earns its cost, since latency
  # is user-facing. Left unreserved by default (see the reserved_concurrent_executions
  # docstring in the module) -- a real deployment fronting real traffic
  # sets this deliberately, per that ADR, rather than inheriting the
  # account default.
}

resource "aws_apigatewayv2_api" "this" {
  name          = "synchronous-api-${var.environment}"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = module.function.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "get_order" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "GET /orders/{orderId}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "post_refund" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "POST /orders/{orderId}/refund"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = module.function.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*"
}
