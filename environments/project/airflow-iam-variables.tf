variable "airflow_iam" {
  description = "Reviewed IAM role, instance profile, and policy attachments used by the Airflow instance. Keep actual values in ignored local tfvars."
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
    managed_policy_attachments = map(object({
      policy_arn = string
    }))
  })
  nullable = false

  validation {
    condition     = can(jsondecode(var.airflow_iam.role.assume_role_policy_json))
    error_message = "The trust policy document must be a valid JSON string."
  }

  validation {
    condition = length(distinct([
      for attachment in values(var.airflow_iam.managed_policy_attachments) : attachment.policy_arn
    ])) == length(var.airflow_iam.managed_policy_attachments)
    error_message = "Managed policy ARNs must be unique."
  }
}
