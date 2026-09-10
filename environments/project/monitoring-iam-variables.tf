variable "monitoring_iam" {
  description = "Reviewed IAM role, instance profile, and policies used by the monitoring instance. Keep actual values in ignored local tfvars."
  type = object({
    role = object({
      name                    = string
      path                    = string
      description             = string
      max_session_duration    = number
      permissions_boundary    = optional(string)
      assume_role_policy_json = string
      tags                    = optional(map(string))
    })
    instance_profile = object({
      name = string
      path = string
      tags = optional(map(string))
    })
    inline_policies = map(object({
      name          = string
      document_json = string
    }))
    managed_policy_attachments = map(object({
      policy_arn = string
    }))
  })
  nullable = false

  validation {
    condition = alltrue([
      for policy in values(var.monitoring_iam.inline_policies) :
      can(jsondecode(policy.document_json))
    ]) && can(jsondecode(var.monitoring_iam.role.assume_role_policy_json))
    error_message = "Trust and inline policy documents must be valid JSON strings."
  }

  validation {
    condition = length(distinct([
      for policy in values(var.monitoring_iam.inline_policies) : policy.name
    ])) == length(var.monitoring_iam.inline_policies)
    error_message = "Inline policy names must be unique."
  }

  validation {
    condition = length(distinct([
      for attachment in values(var.monitoring_iam.managed_policy_attachments) : attachment.policy_arn
    ])) == length(var.monitoring_iam.managed_policy_attachments)
    error_message = "Managed policy ARNs must be unique."
  }
}
