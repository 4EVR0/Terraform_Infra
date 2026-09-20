locals {
  team_admin_role_name  = "4EVR0TeamAdminRole"
  team_admin_role_arn   = "arn:${data.aws_partition.current.partition}:iam::${var.aws_account_id}:role/${local.team_admin_role_name}"
  team_admin_group_name = "4EVR0TeamUsers"
  team_admin_user_arns = sort([
    for name in var.team_admin_user_names :
    "arn:${data.aws_partition.current.partition}:iam::${var.aws_account_id}:user/${name}"
  ])

  team_admin_trust_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowNamedTeamUsersWithMFA"
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { AWS = local.team_admin_user_arns }
      Condition = {
        Bool = { "aws:MultiFactorAuthPresent" = "true" }
      }
    }]
  })

  team_admin_guardrail_policy = jsonencode({
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
        Sid    = "DenyTerraformRoleMutation"
        Effect = "Deny"
        Action = [
          "iam:AttachRolePolicy",
          "iam:DeleteRole",
          "iam:DeleteRolePolicy",
          "iam:DetachRolePolicy",
          "iam:PutRolePolicy",
          "iam:TagRole",
          "iam:UntagRole",
          "iam:UpdateAssumeRolePolicy",
          "iam:UpdateRole",
          "iam:UpdateRoleDescription",
        ]
        Resource = [
          local.terraform_plan_role_arn,
          local.terraform_apply_role_arn,
          local.terraform_bootstrap_admin_role_arn,
          local.team_admin_role_arn,
        ]
      },
      {
        Sid    = "DenyTerraformOperatorMutation"
        Effect = "Deny"
        Action = [
          "iam:AddUserToGroup",
          "iam:AttachUserPolicy",
          "iam:CreateAccessKey",
          "iam:CreateLoginProfile",
          "iam:DeactivateMFADevice",
          "iam:DeleteAccessKey",
          "iam:DeleteLoginProfile",
          "iam:DeleteUser",
          "iam:DeleteUserPolicy",
          "iam:DetachUserPolicy",
          "iam:EnableMFADevice",
          "iam:PutUserPolicy",
          "iam:RemoveUserFromGroup",
          "iam:ResyncMFADevice",
          "iam:TagUser",
          "iam:UntagUser",
          "iam:UpdateAccessKey",
          "iam:UpdateLoginProfile",
          "iam:UpdateUser",
        ]
        Resource = local.terraform_operator_arn
      },
    ]
  })

  team_user_base_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ReadOwnIdentitySettings"
        Effect   = "Allow"
        Action   = ["iam:GetAccountPasswordPolicy", "iam:ListAccountAliases"]
        Resource = "*"
      },
      {
        Sid    = "ManageOwnPasswordAndMFA"
        Effect = "Allow"
        Action = [
          "iam:ChangePassword",
          "iam:DeactivateMFADevice",
          "iam:EnableMFADevice",
          "iam:GetUser",
          "iam:ListMFADevices",
          "iam:ResyncMFADevice",
        ]
        Resource = "arn:${data.aws_partition.current.partition}:iam::${var.aws_account_id}:user/$${aws:username}"
      },
      {
        Sid    = "ManageOwnVirtualMFADevice"
        Effect = "Allow"
        Action = [
          "iam:CreateVirtualMFADevice",
          "iam:DeleteVirtualMFADevice",
        ]
        Resource = "arn:${data.aws_partition.current.partition}:iam::${var.aws_account_id}:mfa/$${aws:username}"
      },
      {
        Sid      = "ListVirtualMFADevices"
        Effect   = "Allow"
        Action   = "iam:ListVirtualMFADevices"
        Resource = "*"
      },
      {
        Sid      = "AssumeTeamAdminRole"
        Effect   = "Allow"
        Action   = "sts:AssumeRole"
        Resource = local.team_admin_role_arn
      },
    ]
  })
}

resource "aws_iam_role" "team_admin" {
  name                 = local.team_admin_role_name
  description          = "MFA-protected shared administrator role for named 4EVR0 team members"
  assume_role_policy   = local.team_admin_trust_policy
  max_session_duration = 7200

  tags = {
    Project   = "4EVR0"
    Purpose   = "team-administration"
    ManagedBy = "Terraform"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_role_policy_attachment" "team_admin" {
  role       = aws_iam_role.team_admin.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AdministratorAccess"

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_role_policy" "team_admin_guardrail" {
  name   = "4EVR0TeamAdminGuardrails"
  role   = aws_iam_role.team_admin.name
  policy = local.team_admin_guardrail_policy

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_group" "team_users" {
  name = local.team_admin_group_name

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_group_policy" "team_users" {
  name   = "4EVR0TeamUserBaseAccess"
  group  = aws_iam_group.team_users.name
  policy = local.team_user_base_policy

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_group_membership" "team_users" {
  name  = "4EVR0TeamUserMembership"
  group = aws_iam_group.team_users.name
  users = sort(tolist(var.team_admin_user_names))
}
