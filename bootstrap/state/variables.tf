variable "aws_account_id" {
  description = "Expected account, provided through ignored local tfvars."
  type        = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "Provide the expected 12-digit account ID."
  }
}

variable "aws_region" {
  type    = string
  default = "ap-northeast-2"
}

variable "state_bucket_name" {
  description = "Globally unique dedicated bucket name, provided through local tfvars."
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$", var.state_bucket_name))
    error_message = "Use 3-63 lowercase letters, digits, and hyphens, starting and ending with a letter or digit."
  }
}
