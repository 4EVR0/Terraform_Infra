# Adopt the existing GraphDB instance without changing its current dependencies.
import {
  to = aws_instance.graphdb
  id = var.instance_ids["graphdb"]
}

# Existing values are provided by an ignored local tfvars file.
resource "aws_instance" "graphdb" {
  ami                                  = var.graphdb_config.ami
  associate_public_ip_address          = var.graphdb_config.associate_public_ip_address
  availability_zone                    = var.graphdb_config.availability_zone
  disable_api_stop                     = var.graphdb_config.disable_api_stop
  disable_api_termination              = var.graphdb_config.disable_api_termination
  ebs_optimized                        = var.graphdb_config.ebs_optimized
  force_destroy                        = var.graphdb_config.force_destroy
  get_password_data                    = var.graphdb_config.get_password_data
  hibernation                          = var.graphdb_config.hibernation
  iam_instance_profile                 = aws_iam_instance_profile.graphdb.name
  instance_initiated_shutdown_behavior = var.graphdb_config.instance_initiated_shutdown_behavior
  instance_type                        = var.graphdb_config.instance_type
  ipv6_addresses                       = var.graphdb_config.ipv6_addresses
  key_name                             = var.graphdb_config.key_name
  monitoring                           = var.graphdb_config.monitoring
  placement_partition_number           = var.graphdb_config.placement_partition_number
  private_ip                           = var.graphdb_config.private_ip
  secondary_private_ips                = var.graphdb_config.secondary_private_ips
  source_dest_check                    = var.graphdb_config.source_dest_check
  subnet_id                            = var.graphdb_config.subnet_id
  tags                                 = var.graphdb_config.tags
  tenancy                              = var.graphdb_config.tenancy
  vpc_security_group_ids = setunion(
    setsubtract(var.graphdb_config.vpc_security_group_ids, [
      var.graphdb_security_group.id,
      var.shared_ssh_security_group.id,
    ]),
    [
      aws_security_group.graphdb.id,
      aws_security_group.shared_ssh.id,
    ],
  )

  capacity_reservation_specification {
    capacity_reservation_preference = var.graphdb_config.capacity_reservation_specification.capacity_reservation_preference
  }

  cpu_options {
    core_count       = var.graphdb_config.cpu_options.core_count
    threads_per_core = var.graphdb_config.cpu_options.threads_per_core
  }

  credit_specification {
    cpu_credits = var.graphdb_config.credit_specification.cpu_credits
  }

  enclave_options {
    enabled = var.graphdb_config.enclave_options.enabled
  }

  maintenance_options {
    auto_recovery = var.graphdb_config.maintenance_options.auto_recovery
  }

  metadata_options {
    http_endpoint               = var.graphdb_config.metadata_options.http_endpoint
    http_protocol_ipv6          = var.graphdb_config.metadata_options.http_protocol_ipv6
    http_put_response_hop_limit = var.graphdb_config.metadata_options.http_put_response_hop_limit
    http_tokens                 = var.graphdb_config.metadata_options.http_tokens
    instance_metadata_tags      = var.graphdb_config.metadata_options.instance_metadata_tags
  }

  private_dns_name_options {
    enable_resource_name_dns_a_record    = var.graphdb_config.private_dns_name_options.enable_resource_name_dns_a_record
    enable_resource_name_dns_aaaa_record = var.graphdb_config.private_dns_name_options.enable_resource_name_dns_aaaa_record
    hostname_type                        = var.graphdb_config.private_dns_name_options.hostname_type
  }

  root_block_device {
    delete_on_termination = var.graphdb_config.root_block_device.delete_on_termination
    encrypted             = var.graphdb_config.root_block_device.encrypted
    iops                  = var.graphdb_config.root_block_device.iops
    tags                  = var.graphdb_config.root_block_device.tags
    throughput            = var.graphdb_config.root_block_device.throughput
    volume_size           = var.graphdb_config.root_block_device.volume_size
    volume_type           = var.graphdb_config.root_block_device.volume_type
  }

  lifecycle {
    prevent_destroy = true

    precondition {
      condition     = var.graphdb_config.iam_instance_profile == var.graphdb_iam.instance_profile.name
      error_message = "The reviewed GraphDB instance profile must match the IAM profile being adopted."
    }

    # Legacy bootstrap data can contain secrets and is intentionally not copied
    # into Terraform configuration. Manage it only after credential rotation.
    ignore_changes = [user_data]
  }
}
