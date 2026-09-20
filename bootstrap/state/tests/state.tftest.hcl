mock_provider "aws" {
  mock_data "aws_partition" {
    defaults = { partition = "aws" }
  }
}

variables {
  aws_account_id                = "000000000000"
  state_bucket_name             = "example-test-terraform-state"
  terraform_operator_user_name  = "example-operator"
  team_admin_user_names         = ["example-team-user-a", "example-team-user-b"]
  terraform_plan_s3_bucket_arns = ["arn:aws:s3:::example-project-bucket"]
  terraform_apply_resources = {
    ec2_instance_arns          = ["arn:aws:ec2:ap-northeast-2:000000000000:instance/i-00000000000000000"]
    ec2_volume_arns            = ["arn:aws:ec2:ap-northeast-2:000000000000:volume/vol-00000000000000000"]
    ec2_security_group_arns    = ["arn:aws:ec2:ap-northeast-2:000000000000:security-group/sg-00000000000000000"]
    iam_role_arns              = ["arn:aws:iam::000000000000:role/example-role"]
    iam_instance_profile_arns  = ["arn:aws:iam::000000000000:instance-profile/example-profile"]
    iam_customer_policy_arns   = ["arn:aws:iam::000000000000:policy/example-policy"]
    iam_attachable_policy_arns = ["arn:aws:iam::aws:policy/example-policy"]
    s3_bucket_arns             = ["arn:aws:s3:::example-project-bucket"]
  }
}

run "protect_plan_role" {
  command = plan

  assert {
    condition     = aws_iam_role.terraform_plan.max_session_duration == 3600
    error_message = "The Terraform plan role session must remain limited to one hour."
  }
  assert {
    condition     = jsondecode(aws_iam_role.terraform_plan.assume_role_policy).Statement[0].Condition.Bool["aws:MultiFactorAuthPresent"] == "true"
    error_message = "The Terraform plan role must require MFA."
  }
  assert {
    condition = alltrue([
      for statement in jsondecode(aws_iam_role_policy.terraform_plan.policy).Statement :
      statement.Sid != "ReadProjectState" || statement.Action == "s3:GetObject"
    ])
    error_message = "The plan role may read the project state but must not write it."
  }
  assert {
    condition = [
      for statement in jsondecode(aws_iam_role_policy.terraform_plan.policy).Statement : statement.Sid
      if try(statement.Action == "s3:DeleteObject", false) || try(contains(statement.Action, "s3:DeleteObject"), false)
    ] == ["ManageProjectStateLock"]
    error_message = "The plan role may delete only the project lock object."
  }
}

run "protect_apply_role" {
  command = plan

  assert {
    condition     = aws_iam_role.terraform_apply.max_session_duration == 3600
    error_message = "The Terraform apply role session must remain limited to one hour."
  }
  assert {
    condition     = jsondecode(aws_iam_role.terraform_apply.assume_role_policy).Statement[0].Condition.Bool["aws:MultiFactorAuthPresent"] == "true"
    error_message = "The Terraform apply role must require MFA."
  }
  assert {
    condition = one([
      for statement in jsondecode(aws_iam_role_policy.terraform_apply.policy).Statement : statement
      if statement.Sid == "WriteProjectState"
    ]).Action == "s3:PutObject"
    error_message = "The apply role may write the project state with PutObject only."
  }
  assert {
    condition = contains(one([
      for statement in jsondecode(aws_iam_role_policy.terraform_apply.policy).Statement : statement
      if statement.Sid == "DenyResourceReplacementAndDeletion"
    ]).Action, "ec2:TerminateInstances")
    error_message = "The apply role must explicitly deny EC2 termination."
  }
}

run "protect_bootstrap_admin_role" {
  command = plan

  assert {
    condition     = aws_iam_role.terraform_bootstrap_admin.max_session_duration == 3600
    error_message = "The Terraform bootstrap administrator session must remain limited to one hour."
  }
  assert {
    condition     = jsondecode(aws_iam_role.terraform_bootstrap_admin.assume_role_policy).Statement[0].Condition.Bool["aws:MultiFactorAuthPresent"] == "true"
    error_message = "The Terraform bootstrap administrator role must require MFA."
  }
  assert {
    condition     = aws_iam_role_policy_attachment.terraform_bootstrap_admin.policy_arn == "arn:aws:iam::aws:policy/AdministratorAccess"
    error_message = "The emergency administrator role must use the reviewed AWS AdministratorAccess policy."
  }
  assert {
    condition = contains(one([
      for statement in jsondecode(aws_iam_role_policy.terraform_bootstrap_admin_guardrail.policy).Statement : statement
      if statement.Sid == "DenyStateDeletion"
    ]).Action, "s3:DeleteObjectVersion")
    error_message = "The bootstrap administrator guardrail must deny deletion of state object versions."
  }
  assert {
    condition = one([
      for statement in jsondecode(aws_iam_role_policy.terraform_bootstrap_admin_guardrail.policy).Statement : statement
      if statement.Sid == "DenyStateBucketDeletion"
    ]).Action == "s3:DeleteBucket"
    error_message = "The bootstrap administrator guardrail must deny state bucket deletion."
  }
}

run "protect_team_admin_role" {
  command = plan

  assert {
    condition     = aws_iam_role.team_admin.max_session_duration == 7200
    error_message = "The shared team administrator role session must remain limited to two hours."
  }
  assert {
    condition     = jsondecode(aws_iam_role.team_admin.assume_role_policy).Statement[0].Condition.Bool["aws:MultiFactorAuthPresent"] == "true"
    error_message = "The shared team administrator role must require MFA."
  }
  assert {
    condition     = length(jsondecode(aws_iam_role.team_admin.assume_role_policy).Statement[0].Principal.AWS) == 2
    error_message = "Only explicitly configured team IAM users may assume the shared administrator role."
  }
  assert {
    condition     = aws_iam_role_policy_attachment.team_admin.policy_arn == "arn:aws:iam::aws:policy/AdministratorAccess"
    error_message = "The shared team administrator role must use the reviewed AWS AdministratorAccess policy."
  }
  assert {
    condition = contains(one([
      for statement in jsondecode(aws_iam_role_policy.team_admin_guardrail.policy).Statement : statement
      if statement.Sid == "DenyTerraformRoleMutation"
    ]).Action, "iam:UpdateAssumeRolePolicy")
    error_message = "Team administrators must not modify Terraform role trust policies."
  }
  assert {
    condition     = aws_iam_group_membership.team_users.users == toset(["example-team-user-a", "example-team-user-b"])
    error_message = "Only configured team users may receive the base access policy."
  }
}

run "protect_state_storage" {
  command = plan

  assert {
    condition     = aws_s3_bucket.state.force_destroy == false
    error_message = "State bucket must not permit forced removal of its contents."
  }
  assert {
    condition = (
      aws_s3_bucket_public_access_block.state.block_public_acls &&
      aws_s3_bucket_public_access_block.state.ignore_public_acls &&
      aws_s3_bucket_public_access_block.state.block_public_policy &&
      aws_s3_bucket_public_access_block.state.restrict_public_buckets
    )
    error_message = "All public access blocks must remain enabled."
  }
  assert {
    condition     = aws_s3_bucket_versioning.state.versioning_configuration[0].status == "Enabled"
    error_message = "Versioning is required for state recovery."
  }
  assert {
    condition     = local.state_keys.bootstrap != local.state_keys.project
    error_message = "Bootstrap and project must not overwrite each other's state."
  }
  assert {
    condition     = aws_s3_bucket_ownership_controls.state.rule[0].object_ownership == "BucketOwnerEnforced"
    error_message = "ACLs must be disabled through bucket ownership enforcement."
  }
  assert {
    condition     = one(aws_s3_bucket_server_side_encryption_configuration.state.rule).apply_server_side_encryption_by_default[0].sse_algorithm == "AES256"
    error_message = "Default server-side encryption must remain enabled."
  }
  assert {
    condition = (
      jsondecode(aws_s3_bucket_policy.state.policy).Statement[0].Effect == "Deny" &&
      jsondecode(aws_s3_bucket_policy.state.policy).Statement[0].Condition.Bool["aws:SecureTransport"] == "false"
    )
    error_message = "The bucket policy must deny insecure requests."
  }
  assert {
    condition = alltrue([
      for policy in values(local.backend_policies) : alltrue([
        for statement in jsondecode(policy).Statement :
        !contains(statement.Action, "s3:DeleteObject") || endswith(statement.Resource, ".tflock")
      ])
    ])
    error_message = "Backend permissions must allow deletion only for lock files, not state files."
  }
  assert {
    condition = alltrue([
      for config in values(output.backend_configs) : config.use_lockfile && config.encrypt
    ])
    error_message = "Both backend templates must enable locking and encryption."
  }
}
