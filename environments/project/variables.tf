variable "aws_account_id" {
  description = "Expected AWS account ID. Set through an ignored local tfvars file."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must contain exactly 12 digits."
  }
}

variable "aws_region" {
  description = "AWS region to inspect."
  type        = string
  default     = "ap-northeast-2"
}

variable "vpc_id" {
  description = "Existing VPC ID. Set through an ignored local tfvars file."
  type        = string

  validation {
    condition     = can(regex("^vpc-([0-9a-f]{8}|[0-9a-f]{17})$", var.vpc_id))
    error_message = "vpc_id must be a valid AWS VPC ID."
  }
}

variable "instance_ids" {
  description = "Logical names mapped to existing EC2 IDs. Keep real values in local tfvars."
  type        = map(string)

  validation {
    condition = length(var.instance_ids) > 0 && alltrue([
      for id in values(var.instance_ids) : can(regex("^i-([0-9a-f]{8}|[0-9a-f]{17})$", id))
    ])
    error_message = "instance_ids must contain at least one valid EC2 instance ID."
  }
}
