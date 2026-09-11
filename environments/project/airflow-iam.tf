resource "aws_iam_role" "airflow" {
  name                 = var.airflow_iam.role.name
  path                 = var.airflow_iam.role.path
  description          = var.airflow_iam.role.description
  max_session_duration = var.airflow_iam.role.max_session_duration
  permissions_boundary = var.airflow_iam.role.permissions_boundary
  assume_role_policy   = var.airflow_iam.role.assume_role_policy_json
  tags                 = var.airflow_iam.role.tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_instance_profile" "airflow" {
  name = var.airflow_iam.instance_profile.name
  path = var.airflow_iam.instance_profile.path
  role = aws_iam_role.airflow.name
  tags = var.airflow_iam.instance_profile.tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_role_policy_attachment" "airflow" {
  for_each = var.airflow_iam.managed_policy_attachments

  role       = aws_iam_role.airflow.name
  policy_arn = each.value.policy_arn

  lifecycle {
    prevent_destroy = true
  }
}

import {
  to = aws_iam_role.airflow
  id = var.airflow_iam.role.name
}

import {
  to = aws_iam_instance_profile.airflow
  id = var.airflow_iam.instance_profile.name
}

import {
  for_each = var.airflow_iam.managed_policy_attachments
  to       = aws_iam_role_policy_attachment.airflow[each.key]
  id       = "${var.airflow_iam.role.name}/${each.value.policy_arn}"
}
