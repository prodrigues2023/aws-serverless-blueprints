# Asynchronous fan-out blueprint (docs/blueprints/async-fanout.md):
#   producer -> SNS topic -> SQS queue -> Lambda -> orders table
#                                 |
#                                 v (on repeated failure)
#                           dead-letter queue
#
# SNS is the fan-out point: this reference config subscribes one queue,
# but the same topic can fan out to several queues/consumers for the
# "several independent things must happen from one event" case
# (async-fanout.md's "when to use", bullet 3) without touching this
# consumer at all.

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
  table_name = "idempotency-keys-async-fanout-${var.environment}"
}

module "queue" {
  source            = "../modules/dead_letter_queue"
  queue_name        = "order-refunds-${var.environment}"
  max_receive_count = 3 # dead-letter-convention.md's provisional retry count
  alarm_actions     = var.dlq_alarm_actions
}

resource "aws_sns_topic" "order_events" {
  name = "order-events-${var.environment}"
}

resource "aws_sqs_queue_policy" "allow_sns" {
  queue_url = module.queue.source_queue_url
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowSNSPublish"
      Effect    = "Allow"
      Principal = { Service = "sns.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = module.queue.source_queue_arn
      Condition = { ArnEquals = { "aws:SourceArn" = aws_sns_topic.order_events.arn } }
    }]
  })
}

resource "aws_sns_topic_subscription" "queue" {
  topic_arn            = aws_sns_topic.order_events.arn
  protocol             = "sqs"
  endpoint             = module.queue.source_queue_arn
  raw_message_delivery = true # the queue's message body is the event envelope itself, not SNS's wrapper
}

module "consumer_role" {
  source              = "../modules/iam_role"
  role_name           = "async-fanout-consumer-${var.environment}-role"
  assume_role_service = "lambda.amazonaws.com"
  statements = [
    {
      sid           = "ConsumeOwnQueue"
      actions       = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
      resources     = [module.queue.source_queue_arn]
      justification = "Consumes and acknowledges messages from its own queue only (iam-role-convention.md's worked example)."
    },
    {
      sid           = "ReadWriteOrdersTable"
      actions       = ["dynamodb:GetItem", "dynamodb:UpdateItem"]
      resources     = [aws_dynamodb_table.orders.arn]
      justification = "Reads order state and writes the refund result."
    },
    {
      sid           = "ReadWriteIdempotencyTable"
      actions       = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]
      resources     = [module.idempotency_table.table_arn]
      justification = "Reads and writes its own dedupe records, keyed on each event's eventId."
    },
  ]
}

module "consumer" {
  source           = "../modules/lambda_function"
  function_name    = "async-fanout-consumer-${var.environment}"
  handler          = "async_fanout.handler.lambda_handler"
  role_arn         = module.consumer_role.role_arn
  source_zip_path  = data.archive_file.handlers.output_path
  source_code_hash = data.archive_file.handlers.output_base64sha256

  # docs/adr/0004-cold-start-and-concurrency.md: consumer concurrency
  # capped to protect the orders table from a burst larger than it (or a
  # downstream it calls) can absorb.
  reserved_concurrent_executions = 10

  environment_variables = {
    ORDERS_TABLE_NAME      = aws_dynamodb_table.orders.name
    IDEMPOTENCY_TABLE_NAME = module.idempotency_table.table_name
  }
}

resource "aws_lambda_event_source_mapping" "queue_to_consumer" {
  event_source_arn = module.queue.source_queue_arn
  function_name    = module.consumer.function_arn
  batch_size       = 10
  # Only the messages the handler actually reports as failed are
  # redelivered -- the rest of the batch is acknowledged even if one
  # message in it fails. See async_fanout/handler.py's docstring.
  function_response_types = ["ReportBatchItemFailures"]
}
