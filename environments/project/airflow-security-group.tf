# Inline ingress/egress blocks must not be mixed with the standalone rule resources.
resource "aws_security_group" "airflow" {
  name        = var.airflow_security_group.name
  description = var.airflow_security_group.description
  vpc_id      = var.airflow_security_group.vpc_id
  tags        = var.airflow_security_group.tags

  lifecycle {
    prevent_destroy = true

    precondition {
      condition     = contains(var.airflow_config.vpc_security_group_ids, var.airflow_security_group.id)
      error_message = "The reviewed group must already be attached to the Airflow instance."
    }
  }
}

resource "aws_vpc_security_group_ingress_rule" "airflow" {
  for_each                     = var.airflow_security_group.ingress
  security_group_id            = aws_security_group.airflow.id
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

resource "aws_vpc_security_group_egress_rule" "airflow" {
  for_each                     = var.airflow_security_group.egress
  security_group_id            = aws_security_group.airflow.id
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
  to = aws_security_group.airflow
  id = var.airflow_security_group.id
}

import {
  for_each = var.airflow_security_group.ingress
  to       = aws_vpc_security_group_ingress_rule.airflow[each.key]
  id       = each.value.id
}

import {
  for_each = var.airflow_security_group.egress
  to       = aws_vpc_security_group_egress_rule.airflow[each.key]
  id       = each.value.id
}
