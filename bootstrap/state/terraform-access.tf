locals {
  terraform_plan_role_name = "4EVR0TerraformPlanRole"
  terraform_plan_role_arn  = "arn:${data.aws_partition.current.partition}:iam::${var.aws_account_id}:role/${local.terraform_plan_role_name}"
  terraform_operator_arn   = "arn:${data.aws_partition.current.partition}:iam::${var.aws_account_id}:user/${var.terraform_operator_user_name}"

  terraform_plan_trust_policy = jsonencode({
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

  terraform_plan_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListProjectStateBucket"
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = local.bucket_arn
        Condition = {
          StringEquals = {
            "s3:prefix" = [
              local.state_keys.project,
              "${local.state_keys.project}.tflock",
            ]
          }
        }
      },
      {
        Sid      = "ReadProjectState"
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = "${local.bucket_arn}/${local.state_keys.project}"
      },
      {
        Sid      = "ManageProjectStateLock"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = "${local.bucket_arn}/${local.state_keys.project}.tflock"
      },
      {
        Sid      = "ReadCallerIdentity"
        Effect   = "Allow"
        Action   = "sts:GetCallerIdentity"
        Resource = "*"
      },
      {
        Sid      = "ReadProjectEC2"
        Effect   = "Allow"
        Action   = "ec2:Describe*"
        Resource = "*"
      },
      {
        Sid    = "ReadProjectIAM"
        Effect = "Allow"
        Action = [
          "iam:GetInstanceProfile",
          "iam:GetPolicy",
          "iam:GetPolicyVersion",
          "iam:GetRole",
          "iam:GetRolePolicy",
          "iam:ListAttachedRolePolicies",
          "iam:ListEntitiesForPolicy",
          "iam:ListInstanceProfilesForRole",
          "iam:ListInstanceProfileTags",
          "iam:ListPolicyTags",
          "iam:ListPolicyVersions",
          "iam:ListRolePolicies",
          "iam:ListRoleTags",
        ]
        Resource = "*"
      },
      {
        Sid    = "ReadProjectS3Configuration"
        Effect = "Allow"
        Action = [
          "s3:GetAccelerateConfiguration",
          "s3:GetBucketAcl",
          "s3:GetBucketCORS",
          "s3:GetBucketLocation",
          "s3:GetBucketLogging",
          "s3:GetBucketNotification",
          "s3:GetBucketObjectLockConfiguration",
          "s3:GetBucketOwnershipControls",
          "s3:GetBucketPolicy",
          "s3:GetBucketPolicyStatus",
          "s3:GetBucketPublicAccessBlock",
          "s3:GetBucketRequestPayment",
          "s3:GetBucketTagging",
          "s3:GetBucketVersioning",
          "s3:GetBucketWebsite",
          "s3:GetEncryptionConfiguration",
          "s3:GetLifecycleConfiguration",
          "s3:GetReplicationConfiguration",
          "s3:ListBucket",
        ]
        Resource = sort(tolist(var.terraform_plan_s3_bucket_arns))
      },
    ]
  })

  terraform_plan_assume_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "AssumeTerraformPlanRole"
      Effect   = "Allow"
      Action   = "sts:AssumeRole"
      Resource = local.terraform_plan_role_arn
    }]
  })
}

resource "aws_iam_role" "terraform_plan" {
  name                 = local.terraform_plan_role_name
  description          = "MFA-protected read-only role for 4EVR0 Terraform plans"
  assume_role_policy   = local.terraform_plan_trust_policy
  max_session_duration = 3600

  tags = {
    Project   = "4EVR0"
    Purpose   = "terraform-plan"
    ManagedBy = "Terraform"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_role_policy" "terraform_plan" {
  name   = "4EVR0TerraformPlanReadOnly"
  role   = aws_iam_role.terraform_plan.name
  policy = local.terraform_plan_policy

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_user_policy" "terraform_plan_assume" {
  name   = "4EVR0AssumeTerraformPlanRole"
  user   = var.terraform_operator_user_name
  policy = local.terraform_plan_assume_policy

  lifecycle {
    prevent_destroy = true
  }
}
