resource "aws_security_group" "graphdb" {
  name        = var.graphdb_security_group.name
  description = var.graphdb_security_group.description
  vpc_id      = var.graphdb_security_group.vpc_id
  tags        = var.graphdb_security_group.tags

  lifecycle {
    prevent_destroy = true

    precondition {
      condition     = contains(var.graphdb_config.vpc_security_group_ids, var.graphdb_security_group.id)
      error_message = "The reviewed group must already be attached to the GraphDB instance."
    }
  }
}

resource "aws_vpc_security_group_ingress_rule" "graphdb" {
  for_each                     = var.graphdb_security_group.ingress
  security_group_id            = aws_security_group.graphdb.id
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

resource "aws_vpc_security_group_egress_rule" "graphdb" {
  for_each                     = var.graphdb_security_group.egress
  security_group_id            = aws_security_group.graphdb.id
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
  to = aws_security_group.graphdb
  id = var.graphdb_security_group.id
}

import {
  for_each = var.graphdb_security_group.ingress
  to       = aws_vpc_security_group_ingress_rule.graphdb[each.key]
  id       = each.value.id
}

import {
  for_each = var.graphdb_security_group.egress
  to       = aws_vpc_security_group_egress_rule.graphdb[each.key]
  id       = each.value.id
}
