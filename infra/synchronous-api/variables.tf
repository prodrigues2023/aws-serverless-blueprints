variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "environment" {
  description = "A short suffix so this blueprint can be deployed more than once (e.g. a sandbox account per developer) without name collisions."
  type        = string
  default     = "dev"
}
