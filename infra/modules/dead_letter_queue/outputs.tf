output "source_queue_arn" {
  value = aws_sqs_queue.source.arn
}

output "source_queue_url" {
  value = aws_sqs_queue.source.id
}

output "dlq_arn" {
  value = aws_sqs_queue.dlq.arn
}

output "dlq_url" {
  value = aws_sqs_queue.dlq.id
}
