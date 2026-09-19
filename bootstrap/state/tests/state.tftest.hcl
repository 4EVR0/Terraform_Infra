mock_provider "aws" {
  mock_data "aws_partition" {
    defaults = { partition = "aws" }
  }
}

variables {
  aws_account_id                = "000000000000"
  state_bucket_name             = "example-test-terraform-state"
  terraform_operator_user_name  = "example-operator"
  terraform_plan_s3_bucket_arns = ["arn:aws:s3:::example-project-bucket"]
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
