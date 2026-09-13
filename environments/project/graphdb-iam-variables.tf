variable "graphdb_iam" {
  description = "Reviewed IAM role, profile, customer-managed policies, and attachments used by GraphDB. Keep actual values in ignored local tfvars."
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
    managed_policies = map(object({
      arn           = string
      name          = string
      path          = string
      description   = optional(string)
      document_json = string
      tags          = optional(map(string))
    }))
    managed_policy_attachments = map(object({
      policy_arn = string
    }))
  })
  nullable = false

  validation {
    condition = can(jsondecode(var.graphdb_iam.role.assume_role_policy_json)) && alltrue([
      for policy in values(var.graphdb_iam.managed_policies) : can(jsondecode(policy.document_json))
    ])
    error_message = "Trust and managed policy documents must be valid JSON strings."
  }

  validation {
    condition = length(distinct([
      for policy in values(var.graphdb_iam.managed_policies) : policy.arn
      ])) == length(var.graphdb_iam.managed_policies) && length(distinct([
      for attachment in values(var.graphdb_iam.managed_policy_attachments) : attachment.policy_arn
    ])) == length(var.graphdb_iam.managed_policy_attachments)
    error_message = "Managed policy and attachment ARNs must be unique."
  }

  validation {
    condition = alltrue([
      for policy in values(var.graphdb_iam.managed_policies) :
      contains([for attachment in values(var.graphdb_iam.managed_policy_attachments) : attachment.policy_arn], policy.arn)
    ])
    error_message = "Every adopted customer-managed policy must be attached to the GraphDB role."
  }
}
