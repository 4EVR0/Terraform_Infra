resource "aws_security_group" "shared_ssh" {
  name        = var.shared_ssh_security_group.name
  description = var.shared_ssh_security_group.description
  vpc_id      = var.shared_ssh_security_group.vpc_id
  tags        = var.shared_ssh_security_group.tags

  lifecycle {
    prevent_destroy = true

    precondition {
      condition = alltrue([
        contains(var.monitoring_config.vpc_security_group_ids, var.shared_ssh_security_group.id),
        contains(var.airflow_config.vpc_security_group_ids, var.shared_ssh_security_group.id),
        contains(var.graphdb_config.vpc_security_group_ids, var.shared_ssh_security_group.id),
      ])
      error_message = "The reviewed shared SSH group must already be attached to every managed project EC2 instance."
    }
  }
}

resource "aws_vpc_security_group_ingress_rule" "shared_ssh" {
  for_each                     = var.shared_ssh_security_group.ingress
  security_group_id            = aws_security_group.shared_ssh.id
  ip_protocol                  = each.value.ip_protocol
  from_port                    = each.value.from_port
  to_port                      = each.value.to_port
  cidr_ipv4                    = each.value.cidr_ipv4
  cidr_ipv6                    = each.value.cidr_ipv6
  prefix_list_id               = each.value.prefix_list_id
  referenced_security_group_id = each.value.referenced_security_group_id
  description                  = each.value.description
  tags                         = each.value.tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_vpc_security_group_egress_rule" "shared_ssh" {
  for_each                     = var.shared_ssh_security_group.egress
  security_group_id            = aws_security_group.shared_ssh.id
  ip_protocol                  = each.value.ip_protocol
  from_port                    = each.value.from_port
  to_port                      = each.value.to_port
  cidr_ipv4                    = each.value.cidr_ipv4
  cidr_ipv6                    = each.value.cidr_ipv6
  prefix_list_id               = each.value.prefix_list_id
  referenced_security_group_id = each.value.referenced_security_group_id
  description                  = each.value.description
  tags                         = each.value.tags

  lifecycle {
    prevent_destroy = true
  }
}

import {
  to = aws_security_group.shared_ssh
  id = var.shared_ssh_security_group.id
}

import {
  for_each = var.shared_ssh_security_group.ingress
  to       = aws_vpc_security_group_ingress_rule.shared_ssh[each.key]
  id       = each.value.id
}

import {
  for_each = var.shared_ssh_security_group.egress
  to       = aws_vpc_security_group_egress_rule.shared_ssh[each.key]
  id       = each.value.id
}
