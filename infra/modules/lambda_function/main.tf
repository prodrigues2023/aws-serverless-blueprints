# Generic Lambda wiring shared by all four blueprints. Event sources
# (API Gateway, SQS, Step Functions, EventBridge Scheduler) are wired in
# each blueprint's own root module, not here, since they differ enough
# per blueprint that forcing them into one generic shape would obscure
# more than it would share.

resource "aws_lambda_function" "this" {
  function_name = var.function_name
  role          = var.role_arn
  handler       = var.handler
  runtime       = var.runtime
  timeout       = var.timeout_seconds
  memory_size   = var.memory_mb

  filename         = var.source_zip_path
  source_code_hash = var.source_code_hash

  reserved_concurrent_executions = var.reserved_concurrent_executions

  environment {
    variables = var.environment_variables
  }

  tags = var.tags
}
