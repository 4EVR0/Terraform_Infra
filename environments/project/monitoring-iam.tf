resource "aws_iam_role" "monitoring" {
  name                 = var.monitoring_iam.role.name
  path                 = var.monitoring_iam.role.path
  description          = var.monitoring_iam.role.description
  max_session_duration = var.monitoring_iam.role.max_session_duration
  permissions_boundary = var.monitoring_iam.role.permissions_boundary
  assume_role_policy   = var.monitoring_iam.role.assume_role_policy_json
  tags                 = var.monitoring_iam.role.tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_instance_profile" "monitoring" {
  name = var.monitoring_iam.instance_profile.name
  path = var.monitoring_iam.instance_profile.path
  role = aws_iam_role.monitoring.name
  tags = var.monitoring_iam.instance_profile.tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_role_policy" "monitoring" {
  for_each = var.monitoring_iam.inline_policies

  name   = each.value.name
  role   = aws_iam_role.monitoring.name
  policy = each.value.document_json

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_role_policy_attachment" "monitoring" {
  for_each = var.monitoring_iam.managed_policy_attachments

  role       = aws_iam_role.monitoring.name
  policy_arn = each.value.policy_arn

  lifecycle {
    prevent_destroy = true
  }
}

import {
  to = aws_iam_role.monitoring
  id = var.monitoring_iam.role.name
}

import {
  to = aws_iam_instance_profile.monitoring
  id = var.monitoring_iam.instance_profile.name
}

import {
  for_each = var.monitoring_iam.inline_policies
  to       = aws_iam_role_policy.monitoring[each.key]
  id       = "${var.monitoring_iam.role.name}:${each.value.name}"
}

import {
  for_each = var.monitoring_iam.managed_policy_attachments
  to       = aws_iam_role_policy_attachment.monitoring[each.key]
  id       = "${var.monitoring_iam.role.name}/${each.value.policy_arn}"
}
