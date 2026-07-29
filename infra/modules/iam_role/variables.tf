variable "role_name" {
  description = "docs/contracts/iam-role-convention.md naming: {service}-{function}-role."
  type        = string
}

variable "assume_role_service" {
  description = "The AWS service principal that assumes this role (lambda.amazonaws.com, states.amazonaws.com, scheduler.amazonaws.com, ...)."
  type        = string
  default     = "lambda.amazonaws.com"
}

variable "statements" {
  description = <<-EOT
    docs/contracts/iam-role-convention.md's statement shape. `justification`
    is Terraform-only -- never sent to AWS, since IAM policy statements have
    no such field -- and exists purely so a reviewer, and the validation
    blocks below, can check the claim against the function's actual code
    path.
  EOT
  type = list(object({
    sid           = string
    actions       = list(string)
    resources     = list(string)
    justification = string
  }))

  validation {
    condition     = alltrue([for s in var.statements : length(trimspace(s.justification)) > 0])
    error_message = "Every statement must carry a non-empty justification (iam-role-convention.md)."
  }

  validation {
    # "Action never service:*" -- reject a trailing bare wildcard segment.
    condition     = alltrue([for s in var.statements : alltrue([for a in s.actions : !endswith(a, ":*") && a != "*"])])
    error_message = "No statement's actions may be a service-wide wildcard (iam-role-convention.md: 'never service:*')."
  }

  validation {
    condition     = alltrue([for s in var.statements : !contains(s.resources, "*")])
    error_message = "No statement's resources may be '*' (iam-role-convention.md: 'a specific ARN, never *')."
  }

  validation {
    condition     = alltrue([for s in var.statements : length(s.actions) > 0 && length(s.resources) > 0])
    error_message = "Every statement must name at least one action and one resource."
  }
}

variable "tags" {
  type    = map(string)
  default = {}
}
