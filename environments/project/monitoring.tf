# Existing values are provided by an ignored local tfvars file.
resource "aws_instance" "monitoring" {
  ami                                  = var.monitoring_config.ami
  associate_public_ip_address          = var.monitoring_config.associate_public_ip_address
  availability_zone                    = var.monitoring_config.availability_zone
  disable_api_stop                     = var.monitoring_config.disable_api_stop
  disable_api_termination              = var.monitoring_config.disable_api_termination
  ebs_optimized                        = var.monitoring_config.ebs_optimized
  force_destroy                        = var.monitoring_config.force_destroy
  get_password_data                    = var.monitoring_config.get_password_data
  hibernation                          = var.monitoring_config.hibernation
  iam_instance_profile                 = var.monitoring_config.iam_instance_profile
  instance_initiated_shutdown_behavior = var.monitoring_config.instance_initiated_shutdown_behavior
  instance_type                        = var.monitoring_config.instance_type
  ipv6_addresses                       = var.monitoring_config.ipv6_addresses
  key_name                             = var.monitoring_config.key_name
  monitoring                           = var.monitoring_config.monitoring
  placement_partition_number           = var.monitoring_config.placement_partition_number
  private_ip                           = var.monitoring_config.private_ip
  secondary_private_ips                = var.monitoring_config.secondary_private_ips
  source_dest_check                    = var.monitoring_config.source_dest_check
  subnet_id                            = var.monitoring_config.subnet_id
  tags                                 = var.monitoring_config.tags
  tenancy                              = var.monitoring_config.tenancy
  vpc_security_group_ids               = var.monitoring_config.vpc_security_group_ids
  capacity_reservation_specification {
    capacity_reservation_preference = var.monitoring_config.capacity_reservation_specification.capacity_reservation_preference
  }
  cpu_options {
    core_count       = var.monitoring_config.cpu_options.core_count
    threads_per_core = var.monitoring_config.cpu_options.threads_per_core
  }
  credit_specification {
    cpu_credits = var.monitoring_config.credit_specification.cpu_credits
  }
  enclave_options {
    enabled = var.monitoring_config.enclave_options.enabled
  }
  maintenance_options {
    auto_recovery = var.monitoring_config.maintenance_options.auto_recovery
  }
  metadata_options {
    http_endpoint               = var.monitoring_config.metadata_options.http_endpoint
    http_protocol_ipv6          = var.monitoring_config.metadata_options.http_protocol_ipv6
    http_put_response_hop_limit = var.monitoring_config.metadata_options.http_put_response_hop_limit
    http_tokens                 = var.monitoring_config.metadata_options.http_tokens
    instance_metadata_tags      = var.monitoring_config.metadata_options.instance_metadata_tags
  }
  private_dns_name_options {
    enable_resource_name_dns_a_record    = var.monitoring_config.private_dns_name_options.enable_resource_name_dns_a_record
    enable_resource_name_dns_aaaa_record = var.monitoring_config.private_dns_name_options.enable_resource_name_dns_aaaa_record
    hostname_type                        = var.monitoring_config.private_dns_name_options.hostname_type
  }
  root_block_device {
    delete_on_termination = var.monitoring_config.root_block_device.delete_on_termination
    encrypted             = var.monitoring_config.root_block_device.encrypted
    iops                  = var.monitoring_config.root_block_device.iops
    tags                  = var.monitoring_config.root_block_device.tags
    throughput            = var.monitoring_config.root_block_device.throughput
    volume_size           = var.monitoring_config.root_block_device.volume_size
    volume_type           = var.monitoring_config.root_block_device.volume_type
  }
  lifecycle {
    prevent_destroy = true
  }
}
