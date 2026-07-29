output "topic_arn" {
  value = aws_sns_topic.order_events.arn
}

output "dlq_url" {
  value = module.queue.dlq_url
}
