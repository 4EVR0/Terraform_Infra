locals {
  terraform_apply_role_name = "4EVR0TerraformApplyRole"
  terraform_apply_role_arn  = "arn:${data.aws_partition.current.partition}:iam::${var.aws_account_id}:role/${local.terraform_apply_role_name}"

  terraform_apply_trust_policy = jsonencode({
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

  terraform_apply_policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      jsondecode(local.terraform_plan_policy).Statement,
      [
        {
          Sid      = "WriteProjectState"
          Effect   = "Allow"
          Action   = "s3:PutObject"
          Resource = "${local.bucket_arn}/${local.state_keys.project}"
        },
        {
          Sid    = "ManageReviewedInstances"
          Effect = "Allow"
          Action = [
            "ec2:ModifyInstanceCreditSpecification",
            "ec2:ModifyInstanceMaintenanceOptions",
            "ec2:ModifyInstanceMetadataOptions",
            "ec2:ModifyPrivateDnsNameOptions",
            "ec2:MonitorInstances",
            "ec2:RebootInstances",
            "ec2:StartInstances",
            "ec2:StopInstances",
            "ec2:UnmonitorInstances",
          ]
          Resource = sort(tolist(var.terraform_apply_resources.ec2_instance_arns))
        },
        {
          Sid    = "ModifyReviewedInstanceAttributes"
          Effect = "Allow"
          Action = [
            "ec2:ModifyInstanceAttribute",
            "ec2:ModifyNetworkInterfaceAttribute",
          ]
          Resource = sort(tolist(setunion(
            var.terraform_apply_resources.ec2_instance_arns,
            var.terraform_apply_resources.ec2_volume_arns,
            var.terraform_apply_resources.ec2_security_group_arns,
          )))
        },
        {
          Sid    = "ManageReviewedSecurityGroupRules"
          Effect = "Allow"
          Action = [
            "ec2:AuthorizeSecurityGroupEgress",
            "ec2:AuthorizeSecurityGroupIngress",
            "ec2:ModifySecurityGroupRules",
            "ec2:RevokeSecurityGroupEgress",
            "ec2:RevokeSecurityGroupIngress",
            "ec2:UpdateSecurityGroupRuleDescriptionsEgress",
            "ec2:UpdateSecurityGroupRuleDescriptionsIngress",
          ]
          Resource = sort(tolist(var.terraform_apply_resources.ec2_security_group_arns))
        },
        {
          Sid    = "TagReviewedEC2Resources"
          Effect = "Allow"
          Action = ["ec2:CreateTags", "ec2:DeleteTags"]
          Resource = sort(tolist(setunion(
            var.terraform_apply_resources.ec2_instance_arns,
            var.terraform_apply_resources.ec2_volume_arns,
            var.terraform_apply_resources.ec2_security_group_arns,
          )))
        },
        {
          Sid    = "ManageReviewedIAMRoles"
          Effect = "Allow"
          Action = [
            "iam:PutRolePolicy",
            "iam:DeleteRolePolicy",
            "iam:TagRole",
            "iam:UntagRole",
            "iam:UpdateAssumeRolePolicy",
            "iam:UpdateRole",
            "iam:UpdateRoleDescription",
          ]
          Resource = sort(tolist(var.terraform_apply_resources.iam_role_arns))
        },
        {
          Sid      = "ManageReviewedRolePolicyAttachments"
          Effect   = "Allow"
          Action   = ["iam:AttachRolePolicy", "iam:DetachRolePolicy"]
          Resource = sort(tolist(var.terraform_apply_resources.iam_role_arns))
          Condition = {
            ArnEquals = {
              "iam:PolicyARN" = sort(tolist(var.terraform_apply_resources.iam_attachable_policy_arns))
            }
          }
        },
        {
          Sid    = "ManageReviewedInstanceProfiles"
          Effect = "Allow"
          Action = [
            "iam:AddRoleToInstanceProfile",
            "iam:RemoveRoleFromInstanceProfile",
            "iam:TagInstanceProfile",
            "iam:UntagInstanceProfile",
          ]
          Resource = sort(tolist(var.terraform_apply_resources.iam_instance_profile_arns))
        },
        {
          Sid    = "ManageReviewedCustomerPolicies"
          Effect = "Allow"
          Action = [
            "iam:CreatePolicyVersion",
            "iam:DeletePolicyVersion",
            "iam:SetDefaultPolicyVersion",
            "iam:TagPolicy",
            "iam:UntagPolicy",
          ]
          Resource = sort(tolist(var.terraform_apply_resources.iam_customer_policy_arns))
        },
        {
          Sid      = "PassReviewedRolesToEC2"
          Effect   = "Allow"
          Action   = "iam:PassRole"
          Resource = sort(tolist(var.terraform_apply_resources.iam_role_arns))
          Condition = {
            StringEquals = { "iam:PassedToService" = "ec2.amazonaws.com" }
          }
        },
        {
          Sid    = "ManageReviewedS3Protection"
          Effect = "Allow"
          Action = [
            "s3:PutBucketOwnershipControls",
            "s3:PutBucketPublicAccessBlock",
            "s3:PutBucketTagging",
            "s3:PutEncryptionConfiguration",
          ]
          Resource = sort(tolist(var.terraform_apply_resources.s3_bucket_arns))
        },
        {
          Sid    = "DenyProjectStateDeletion"
          Effect = "Deny"
          Action = "s3:DeleteObject"
          Resource = [
            "${local.bucket_arn}/${local.state_keys.project}",
            "${local.bucket_arn}/${local.state_keys.bootstrap}",
          ]
        },
        {
          Sid      = "DenyBootstrapStateAccess"
          Effect   = "Deny"
          Action   = ["s3:GetObject", "s3:PutObject"]
          Resource = "${local.bucket_arn}/${local.state_keys.bootstrap}"
        },
        {
          Sid    = "DenyResourceReplacementAndDeletion"
          Effect = "Deny"
          Action = [
            "ec2:CreateNetworkInterface",
            "ec2:CreateSecurityGroup",
            "ec2:CreateVolume",
            "ec2:DeleteNetworkInterface",
            "ec2:DeleteSecurityGroup",
            "ec2:DeleteVolume",
            "ec2:RunInstances",
            "ec2:TerminateInstances",
            "iam:CreateInstanceProfile",
            "iam:CreatePolicy",
            "iam:CreateRole",
            "iam:DeleteInstanceProfile",
            "iam:DeletePolicy",
            "iam:DeleteRole",
            "s3:CreateBucket",
            "s3:DeleteBucket",
          ]
          Resource = "*"
        },
      ]
    )
  })

  terraform_apply_assume_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "AssumeTerraformApplyRole"
      Effect   = "Allow"
      Action   = "sts:AssumeRole"
      Resource = local.terraform_apply_role_arn
    }]
  })
}

resource "aws_iam_role" "terraform_apply" {
  name                 = local.terraform_apply_role_name
  description          = "MFA-protected role for reviewed 4EVR0 Terraform in-place changes"
  assume_role_policy   = local.terraform_apply_trust_policy
  max_session_duration = 3600

  tags = {
    Project   = "4EVR0"
    Purpose   = "terraform-apply"
    ManagedBy = "Terraform"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_role_policy" "terraform_apply" {
  name   = "4EVR0TerraformApplyRestricted"
  role   = aws_iam_role.terraform_apply.name
  policy = local.terraform_apply_policy

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_user_policy" "terraform_apply_assume" {
  name   = "4EVR0AssumeTerraformApplyRole"
  user   = var.terraform_operator_user_name
  policy = local.terraform_apply_assume_policy

  lifecycle {
    prevent_destroy = true
  }
}
