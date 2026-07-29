variable "function_name" {
  type = string
}

variable "handler" {
  description = "Python entrypoint, e.g. 'synchronous_api.handler.lambda_handler'."
  type        = string
}

variable "role_arn" {
  type = string
}

variable "source_zip_path" {
  description = "Path to the deployment package. All four blueprints share one package (the whole handlers/ directory, including shared/) and differ only in `handler` -- see infra/README.md for why."
  type        = string
}

variable "source_code_hash" {
  type = string
}

variable "environment_variables" {
  type    = map(string)
  default = {}
}

variable "timeout_seconds" {
  type    = number
  default = 10
}

variable "memory_mb" {
  type    = number
  default = 128
}

variable "runtime" {
  type    = string
  default = "python3.12"
}

variable "reserved_concurrent_executions" {
  description = <<-EOT
    docs/adr/0004-cold-start-and-concurrency.md: a bound on this function's
    concurrency, to protect a downstream that cannot scale as fast as
    Lambda can. -1 (the default) means unreserved -- set explicitly for any
    function in front of a downstream with its own concurrency limit.
  EOT
  type        = number
  default     = -1
}

variable "tags" {
  type    = map(string)
  default = {}
}
