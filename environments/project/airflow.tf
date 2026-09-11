# Adopt the existing Airflow instance without changing its current dependencies.
import {
  to = aws_instance.airflow
  id = var.instance_ids["airflow"]
}

# Existing values are provided by an ignored local tfvars file.
resource "aws_instance" "airflow" {
  ami                                  = var.airflow_config.ami
  associate_public_ip_address          = var.airflow_config.associate_public_ip_address
  availability_zone                    = var.airflow_config.availability_zone
  disable_api_stop                     = var.airflow_config.disable_api_stop
  disable_api_termination              = var.airflow_config.disable_api_termination
  ebs_optimized                        = var.airflow_config.ebs_optimized
  force_destroy                        = var.airflow_config.force_destroy
  get_password_data                    = var.airflow_config.get_password_data
  hibernation                          = var.airflow_config.hibernation
  iam_instance_profile                 = aws_iam_instance_profile.airflow.name
  instance_initiated_shutdown_behavior = var.airflow_config.instance_initiated_shutdown_behavior
  instance_type                        = var.airflow_config.instance_type
  ipv6_addresses                       = var.airflow_config.ipv6_addresses
  key_name                             = var.airflow_config.key_name
  monitoring                           = var.airflow_config.monitoring
  placement_partition_number           = var.airflow_config.placement_partition_number
  private_ip                           = var.airflow_config.private_ip
  secondary_private_ips                = var.airflow_config.secondary_private_ips
  source_dest_check                    = var.airflow_config.source_dest_check
  subnet_id                            = var.airflow_config.subnet_id
  tags                                 = var.airflow_config.tags
  tenancy                              = var.airflow_config.tenancy
  vpc_security_group_ids = setunion(
    setsubtract(var.airflow_config.vpc_security_group_ids, [var.airflow_security_group.id]),
    [aws_security_group.airflow.id],
  )

  capacity_reservation_specification {
    capacity_reservation_preference = var.airflow_config.capacity_reservation_specification.capacity_reservation_preference
  }

  cpu_options {
    core_count       = var.airflow_config.cpu_options.core_count
    threads_per_core = var.airflow_config.cpu_options.threads_per_core
  }

  credit_specification {
    cpu_credits = var.airflow_config.credit_specification.cpu_credits
  }

  enclave_options {
    enabled = var.airflow_config.enclave_options.enabled
  }

  maintenance_options {
    auto_recovery = var.airflow_config.maintenance_options.auto_recovery
  }

  metadata_options {
    http_endpoint               = var.airflow_config.metadata_options.http_endpoint
    http_protocol_ipv6          = var.airflow_config.metadata_options.http_protocol_ipv6
    http_put_response_hop_limit = var.airflow_config.metadata_options.http_put_response_hop_limit
    http_tokens                 = var.airflow_config.metadata_options.http_tokens
    instance_metadata_tags      = var.airflow_config.metadata_options.instance_metadata_tags
  }

  private_dns_name_options {
    enable_resource_name_dns_a_record    = var.airflow_config.private_dns_name_options.enable_resource_name_dns_a_record
    enable_resource_name_dns_aaaa_record = var.airflow_config.private_dns_name_options.enable_resource_name_dns_aaaa_record
    hostname_type                        = var.airflow_config.private_dns_name_options.hostname_type
  }

  root_block_device {
    delete_on_termination = var.airflow_config.root_block_device.delete_on_termination
    encrypted             = var.airflow_config.root_block_device.encrypted
    iops                  = var.airflow_config.root_block_device.iops
    tags                  = var.airflow_config.root_block_device.tags
    throughput            = var.airflow_config.root_block_device.throughput
    volume_size           = var.airflow_config.root_block_device.volume_size
    volume_type           = var.airflow_config.root_block_device.volume_type
  }

  lifecycle {
    prevent_destroy = true

    precondition {
      condition     = var.airflow_config.iam_instance_profile == var.airflow_iam.instance_profile.name
      error_message = "The reviewed Airflow instance profile must match the IAM profile being adopted."
    }
  }
}
