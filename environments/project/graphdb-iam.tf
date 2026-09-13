resource "aws_iam_role" "graphdb" {
  name                 = var.graphdb_iam.role.name
  path                 = var.graphdb_iam.role.path
  description          = var.graphdb_iam.role.description
  max_session_duration = var.graphdb_iam.role.max_session_duration
  permissions_boundary = var.graphdb_iam.role.permissions_boundary
  assume_role_policy   = var.graphdb_iam.role.assume_role_policy_json
  tags                 = var.graphdb_iam.role.tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_instance_profile" "graphdb" {
  name = var.graphdb_iam.instance_profile.name
  path = var.graphdb_iam.instance_profile.path
  role = aws_iam_role.graphdb.name
  tags = var.graphdb_iam.instance_profile.tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_policy" "graphdb" {
  for_each = var.graphdb_iam.managed_policies

  name        = each.value.name
  path        = each.value.path
  description = each.value.description
  policy      = each.value.document_json
  tags        = each.value.tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_role_policy_attachment" "graphdb" {
  for_each = var.graphdb_iam.managed_policy_attachments

  role       = aws_iam_role.graphdb.name
  policy_arn = each.value.policy_arn

  lifecycle {
    prevent_destroy = true
  }
}

import {
  to = aws_iam_role.graphdb
  id = var.graphdb_iam.role.name
}

import {
  to = aws_iam_instance_profile.graphdb
  id = var.graphdb_iam.instance_profile.name
}

import {
  for_each = var.graphdb_iam.managed_policies
  to       = aws_iam_policy.graphdb[each.key]
  id       = each.value.arn
}

import {
  for_each = var.graphdb_iam.managed_policy_attachments
  to       = aws_iam_role_policy_attachment.graphdb[each.key]
  id       = "${var.graphdb_iam.role.name}/${each.value.policy_arn}"
}
