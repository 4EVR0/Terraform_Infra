locals {
  terraform_bootstrap_admin_role_name = "4EVR0TerraformBootstrapAdminRole"
  terraform_bootstrap_admin_role_arn  = "arn:${data.aws_partition.current.partition}:iam::${var.aws_account_id}:role/${local.terraform_bootstrap_admin_role_name}"

  terraform_bootstrap_admin_trust_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowOperatorWithMFA"
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { AWS = local.terraform_operator_arn }
      Condition = {
        Bool = { "aws:MultiFactorAuthPresent" = "true" }
      }
    }]
  })

  terraform_bootstrap_admin_guardrail_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyStateDeletion"
        Effect = "Deny"
        Action = [
          "s3:DeleteObject",
          "s3:DeleteObjectVersion",
        ]
        Resource = [
          "${local.bucket_arn}/${local.state_keys.bootstrap}",
          "${local.bucket_arn}/${local.state_keys.project}",
        ]
      },
      {
        Sid      = "DenyStateBucketDeletion"
        Effect   = "Deny"
        Action   = "s3:DeleteBucket"
        Resource = local.bucket_arn
      },
      {
        Sid    = "DenyTerraformRoleDeletion"
        Effect = "Deny"
        Action = "iam:DeleteRole"
        Resource = [
          local.terraform_plan_role_arn,
          local.terraform_apply_role_arn,
          local.terraform_bootstrap_admin_role_arn,
        ]
      },
      {
        Sid      = "DenyOperatorDeletion"
        Effect   = "Deny"
        Action   = "iam:DeleteUser"
        Resource = local.terraform_operator_arn
      },
    ]
  })

  terraform_bootstrap_admin_assume_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "AssumeTerraformBootstrapAdminRole"
      Effect   = "Allow"
      Action   = "sts:AssumeRole"
      Resource = local.terraform_bootstrap_admin_role_arn
    }]
  })
}

resource "aws_iam_role" "terraform_bootstrap_admin" {
  name                 = local.terraform_bootstrap_admin_role_name
  description          = "MFA-protected emergency administrator role for 4EVR0 Terraform bootstrap recovery"
  assume_role_policy   = local.terraform_bootstrap_admin_trust_policy
  max_session_duration = 3600

  tags = {
    Project   = "4EVR0"
    Purpose   = "terraform-bootstrap-admin"
    ManagedBy = "Terraform"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_role_policy_attachment" "terraform_bootstrap_admin" {
  role       = aws_iam_role.terraform_bootstrap_admin.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AdministratorAccess"

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_role_policy" "terraform_bootstrap_admin_guardrail" {
  name   = "4EVR0TerraformBootstrapAdminGuardrails"
  role   = aws_iam_role.terraform_bootstrap_admin.name
  policy = local.terraform_bootstrap_admin_guardrail_policy

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_user_policy" "terraform_bootstrap_admin_assume" {
  name   = "4EVR0AssumeTerraformBootstrapAdminRole"
  user   = var.terraform_operator_user_name
  policy = local.terraform_bootstrap_admin_assume_policy

  lifecycle {
    prevent_destroy = true
  }
}
