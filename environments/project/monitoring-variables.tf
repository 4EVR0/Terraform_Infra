variable "monitoring_config" {
  description = "Reviewed existing EC2 configuration; keep actual values in ignored local tfvars."
  type = object({
    ami                                  = string
    associate_public_ip_address          = bool
    availability_zone                    = string
    disable_api_stop                     = bool
    disable_api_termination              = bool
    ebs_optimized                        = bool
    force_destroy                        = bool
    get_password_data                    = bool
    hibernation                          = bool
    iam_instance_profile                 = string
    instance_initiated_shutdown_behavior = string
    instance_type                        = string
    ipv6_addresses                       = set(string)
    key_name                             = string
    monitoring                           = bool
    placement_partition_number           = number
    private_ip                           = string
    secondary_private_ips                = set(string)
    source_dest_check                    = bool
    subnet_id                            = string
    tags                                 = map(string)
    tenancy                              = string
    vpc_security_group_ids               = set(string)
    capacity_reservation_specification = object({
      capacity_reservation_preference = string
    })
    cpu_options = object({
      core_count       = number
      threads_per_core = number
    })
    credit_specification = object({
      cpu_credits = string
    })
    enclave_options = object({
      enabled = bool
    })
    maintenance_options = object({
      auto_recovery = string
    })
    metadata_options = object({
      http_endpoint               = string
      http_protocol_ipv6          = string
      http_put_response_hop_limit = number
      http_tokens                 = string
      instance_metadata_tags      = string
    })
    private_dns_name_options = object({
      enable_resource_name_dns_a_record    = bool
      enable_resource_name_dns_aaaa_record = bool
      hostname_type                        = string
    })
    root_block_device = object({
      delete_on_termination = bool
      encrypted             = bool
      iops                  = number
      tags                  = map(string)
      throughput            = number
      volume_size           = number
      volume_type           = string
    })
  })
  nullable = false
}
