variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "schedule_expression" {
  description = "When the batch job runs. Nightly at 02:00 UTC by default -- nobody is waiting, so this is chosen for low contention on the account's other scheduled work, not for any latency reason (scheduled-batch.md: cold start is irrelevant here)."
  type        = string
  default     = "cron(0 2 * * ? *)"
}
