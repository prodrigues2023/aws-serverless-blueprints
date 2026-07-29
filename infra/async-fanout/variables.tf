variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "dlq_alarm_actions" {
  description = "ARNs (typically an SNS topic) notified when the DLQ receives a message. Empty by default -- see modules/dead_letter_queue's warning about what that means."
  type        = list(string)
  default     = []
}
