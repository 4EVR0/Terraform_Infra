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

variable "terraform_operator_user_name" {
  description = "Existing human IAM user allowed to assume the MFA-protected Terraform plan role. Set through ignored local tfvars."
  type        = string
  nullable    = false

  validation {
    condition     = can(regex("^[A-Za-z0-9+=,.@_-]{1,64}$", var.terraform_operator_user_name))
    error_message = "terraform_operator_user_name must be a valid IAM user name."
  }
}

variable "terraform_plan_s3_bucket_arns" {
  description = "Project S3 bucket ARNs whose configuration Terraform must read during plan. Keep actual ARNs in ignored local tfvars."
  type        = set(string)
  nullable    = false

  validation {
    condition = length(var.terraform_plan_s3_bucket_arns) > 0 && alltrue([
      for arn in var.terraform_plan_s3_bucket_arns : can(regex("^arn:[^:]+:s3:::[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", arn))
    ])
    error_message = "terraform_plan_s3_bucket_arns must contain at least one valid S3 bucket ARN."
  }
}
