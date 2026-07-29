# Scheduled/batch blueprint (docs/blueprints/scheduled-batch.md):
#   EventBridge Scheduler -> Lambda -> iterate the orders table
#
# The schedule's target input embeds the Scheduler context attribute
# <aws.scheduler.scheduled-time> -- the *intended* fire time, not the
# actual invocation time -- exactly what idempotency-convention.md's
# "scheduled/batch: run identity" note requires the key to be built from,
# so a retried invocation of the same scheduled run shares its key with
# the original.

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
  table_name = "idempotency-keys-scheduled-batch-${var.environment}"
}

locals {
  schedule_name = "nightly-close-stale-orders-${var.environment}"
}

module "function_role" {
  source              = "../modules/iam_role"
  role_name           = "scheduled-batch-handler-${var.environment}-role"
  assume_role_service = "lambda.amazonaws.com"
  statements = [
    {
      sid           = "ScanAndCloseOrdersTable"
      actions       = ["dynamodb:Scan", "dynamodb:UpdateItem"]
      resources     = [aws_dynamodb_table.orders.arn]
      justification = "Scans the whole table to find delivered orders and closes them -- the one blueprint here that legitimately needs Scan, since it is a full-table batch job by design, not a per-item lookup."
    },
    {
      sid           = "ReadWriteIdempotencyTable"
      actions       = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]
      resources     = [module.idempotency_table.table_arn]
      justification = "Reads and writes the run-level dedupe record keyed on {scheduleName}:{scheduledFireTime}."
    },
  ]
}

module "function" {
  source           = "../modules/lambda_function"
  function_name    = "scheduled-batch-handler-${var.environment}"
  handler          = "scheduled_batch.handler.lambda_handler"
  role_arn         = module.function_role.role_arn
  source_zip_path  = data.archive_file.handlers.output_path
  source_code_hash = data.archive_file.handlers.output_base64sha256
  timeout_seconds  = 60 # a full-table scan gets more room than the other blueprints' request-latency-bound functions

  environment_variables = {
    ORDERS_TABLE_NAME      = aws_dynamodb_table.orders.name
    IDEMPOTENCY_TABLE_NAME = module.idempotency_table.table_name
    SCHEDULE_NAME          = local.schedule_name
  }
}

module "scheduler_role" {
  source              = "../modules/iam_role"
  role_name           = "scheduled-batch-invoker-${var.environment}-role"
  assume_role_service = "scheduler.amazonaws.com"
  statements = [
    {
      sid           = "InvokeBatchHandler"
      actions       = ["lambda:InvokeFunction"]
      resources     = [module.function.function_arn]
      justification = "EventBridge Scheduler's own least-privilege role: invoke exactly the one Lambda this schedule targets."
    },
  ]
}

resource "aws_scheduler_schedule" "nightly_close" {
  name                         = local.schedule_name
  schedule_expression          = var.schedule_expression
  schedule_expression_timezone = "UTC"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = module.function.function_arn
    role_arn = module.scheduler_role.role_arn
    input    = jsonencode({ scheduledFireTime = "<aws.scheduler.scheduled-time>" })
  }
}
