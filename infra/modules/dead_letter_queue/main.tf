# docs/contracts/dead-letter-convention.md: a source queue, a DLQ named
# '{queue}-dlq', a redrive policy after max_receive_count attempts, 14-day
# DLQ retention, and a CloudWatch alarm on ApproximateNumberOfMessagesVisible
# > 0 with no delay and no batching window -- one message is the threshold,
# not some count meant to filter noise, because a DLQ is defined by
# ADR-0003 as something nothing should be routinely landing in.

resource "aws_sqs_queue" "dlq" {
  name                      = "${var.queue_name}-dlq"
  message_retention_seconds = 14 * 24 * 60 * 60 # SQS's maximum -- the longest runway for a human to respond
  tags                      = var.tags
}

resource "aws_sqs_queue" "source" {
  name                       = var.queue_name
  visibility_timeout_seconds = var.visibility_timeout_seconds
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.max_receive_count
  })
  tags = var.tags
}

# The DLQ's own redrive-allow policy: only the source queue above may
# redrive *into* this DLQ, and (via redrive_permission) messages may be
# moved back out to the source queue for the replay step
# (dead-letter-convention.md's manual, human-triggered replay -- this
# permission enables that operation, it does not automate it).
resource "aws_sqs_queue_redrive_allow_policy" "dlq" {
  queue_url = aws_sqs_queue.dlq.id
  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.source.arn]
  })
}

resource "aws_cloudwatch_metric_alarm" "dlq_not_empty" {
  alarm_name          = "${var.queue_name}-dlq-not-empty"
  alarm_description   = "docs/contracts/dead-letter-convention.md: any message in ${var.queue_name}-dlq is an alert, not routine traffic."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  dimensions          = { QueueName = aws_sqs_queue.dlq.name }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_actions
  tags                = var.tags
}
