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
  description = "Existing human IAM user allowed to assume the MFA-protected Terraform roles. Set through ignored local tfvars."
  type        = string
  nullable    = false

  validation {
    condition     = can(regex("^[A-Za-z0-9+=,.@_-]{1,64}$", var.terraform_operator_user_name))
    error_message = "terraform_operator_user_name must be a valid IAM user name."
  }
}

variable "team_admin_user_names" {
  description = "Existing human IAM users allowed to assume the MFA-protected shared team administrator role. Set through ignored local tfvars."
  type        = set(string)
  nullable    = false

  validation {
    condition = length(var.team_admin_user_names) > 0 && alltrue([
      for name in var.team_admin_user_names : can(regex("^[A-Za-z0-9+=,.@_-]{1,64}$", name))
    ])
    error_message = "team_admin_user_names must contain at least one valid IAM user name."
  }

  validation {
    condition     = !contains(var.team_admin_user_names, var.terraform_operator_user_name)
    error_message = "The dedicated Terraform operator must not also be a shared team administrator user."
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

variable "terraform_apply_resources" {
  description = "Existing project resource ARNs that the Terraform apply role may change. Keep actual ARNs in ignored local tfvars."
  type = object({
    ec2_instance_arns          = set(string)
    ec2_volume_arns            = set(string)
    ec2_security_group_arns    = set(string)
    iam_role_arns              = set(string)
    iam_instance_profile_arns  = set(string)
    iam_customer_policy_arns   = set(string)
    iam_attachable_policy_arns = set(string)
    s3_bucket_arns             = set(string)
  })
  nullable = false

  validation {
    condition = alltrue([
      length(var.terraform_apply_resources.ec2_instance_arns) > 0,
      length(var.terraform_apply_resources.ec2_volume_arns) > 0,
      length(var.terraform_apply_resources.ec2_security_group_arns) > 0,
      length(var.terraform_apply_resources.iam_role_arns) > 0,
      length(var.terraform_apply_resources.iam_instance_profile_arns) > 0,
      length(var.terraform_apply_resources.iam_customer_policy_arns) > 0,
      length(var.terraform_apply_resources.iam_attachable_policy_arns) > 0,
      length(var.terraform_apply_resources.s3_bucket_arns) > 0,
    ])
    error_message = "terraform_apply_resources must contain every reviewed project resource category."
  }

  validation {
    condition = alltrue(concat(
      [for arn in var.terraform_apply_resources.ec2_instance_arns : can(regex("^arn:[^:]+:ec2:[^:]+:[0-9]{12}:instance/i-[0-9a-f]{8,17}$", arn))],
      [for arn in var.terraform_apply_resources.ec2_volume_arns : can(regex("^arn:[^:]+:ec2:[^:]+:[0-9]{12}:volume/vol-[0-9a-f]{8,17}$", arn))],
      [for arn in var.terraform_apply_resources.ec2_security_group_arns : can(regex("^arn:[^:]+:ec2:[^:]+:[0-9]{12}:security-group/sg-[0-9a-f]{8,17}$", arn))],
      [for arn in var.terraform_apply_resources.iam_role_arns : can(regex("^arn:[^:]+:iam::[0-9]{12}:role/.+$", arn)) && !strcontains(arn, "*")],
      [for arn in var.terraform_apply_resources.iam_instance_profile_arns : can(regex("^arn:[^:]+:iam::[0-9]{12}:instance-profile/.+$", arn)) && !strcontains(arn, "*")],
      [for arn in var.terraform_apply_resources.iam_customer_policy_arns : can(regex("^arn:[^:]+:iam::[0-9]{12}:policy/.+$", arn)) && !strcontains(arn, "*")],
      [for arn in var.terraform_apply_resources.iam_attachable_policy_arns : can(regex("^arn:[^:]+:iam::(aws|[0-9]{12}):policy/.+$", arn)) && !strcontains(arn, "*")],
      [for arn in var.terraform_apply_resources.s3_bucket_arns : can(regex("^arn:[^:]+:s3:::[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", arn))],
    ))
    error_message = "terraform_apply_resources must contain explicit ARNs of the expected resource types; wildcard ARNs are not allowed."
  }
}
