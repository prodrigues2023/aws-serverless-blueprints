variable "queue_name" {
  description = "The source queue's name. The DLQ is named '{queue_name}-dlq' per docs/contracts/dead-letter-convention.md."
  type        = string
}

variable "max_receive_count" {
  description = "Attempts before a message moves to the DLQ. Provisional at 3 per dead-letter-convention.md."
  type        = number
  default     = 3
}

variable "visibility_timeout_seconds" {
  description = "Should be >= the consuming Lambda's timeout (a message must stay invisible for at least as long as the function might run)."
  type        = number
  default     = 30
}

variable "alarm_actions" {
  description = "ARNs notified when the DLQ receives a message (an SNS topic, typically). Empty by default; a deployment without at least one action here has an alarm that fires into nothing, which is the 'silent grave' dead-letter-convention.md warns against -- set this."
  type        = list(string)
  default     = []
}

variable "tags" {
  type    = map(string)
  default = {}
}
