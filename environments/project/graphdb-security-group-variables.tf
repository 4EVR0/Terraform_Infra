variable "graphdb_security_group" {
  description = "Reviewed GraphDB-only security group and existing rule IDs. Keep actual values in ignored local tfvars."
  type = object({
    id          = string
    name        = string
    description = string
    vpc_id      = string
    tags        = map(string)
    ingress = map(object({
      id                           = string
      ip_protocol                  = string
      from_port                    = optional(number)
      to_port                      = optional(number)
      cidr_ipv4                    = optional(string)
      cidr_ipv6                    = optional(string)
      prefix_list_id               = optional(string)
      referenced_security_group_id = optional(string)
      description                  = optional(string)
      tags                         = optional(map(string))
    }))
    egress = map(object({
      id                           = string
      ip_protocol                  = string
      from_port                    = optional(number)
      to_port                      = optional(number)
      cidr_ipv4                    = optional(string)
      cidr_ipv6                    = optional(string)
      prefix_list_id               = optional(string)
      referenced_security_group_id = optional(string)
      description                  = optional(string)
      tags                         = optional(map(string))
    }))
  })
  nullable = false

  validation {
    condition = alltrue([
      for rule in concat(values(var.graphdb_security_group.ingress), values(var.graphdb_security_group.egress)) :
      length([for source in [rule.cidr_ipv4, rule.cidr_ipv6, rule.prefix_list_id, rule.referenced_security_group_id] : source if source != null]) == 1
    ])
    error_message = "Each rule must specify exactly one CIDR, prefix list, or referenced security group."
  }
}
