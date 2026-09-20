output "backend_configs" {
  description = "Configuration templates to save locally as ignored .tfbackend files after creation."
  sensitive   = true
  value = {
    for scope, key in local.state_keys : scope => {
      bucket              = var.state_bucket_name
      key                 = key
      region              = var.aws_region
      encrypt             = true
      use_lockfile        = true
      allowed_account_ids = [var.aws_account_id]
    }
  }
}

output "backend_policies" {
  description = "Unattached IAM policy templates. These grant backend access, not infrastructure management."
  sensitive   = true
  value       = local.backend_policies
}

output "terraform_plan_role_arn" {
  description = "ARN used by the local AWS CLI profile for MFA-protected Terraform plans."
  sensitive   = true
  value       = local.terraform_plan_role_arn
}

output "terraform_apply_role_arn" {
  description = "ARN used by the local AWS CLI profile for MFA-protected reviewed Terraform applies."
  sensitive   = true
  value       = local.terraform_apply_role_arn
}

output "terraform_bootstrap_admin_role_arn" {
  description = "ARN used by the local AWS CLI profile for MFA-protected bootstrap recovery and emergency administration."
  sensitive   = true
  value       = local.terraform_bootstrap_admin_role_arn
}

output "team_admin_role_arn" {
  description = "ARN used by named team members for MFA-protected temporary administrator sessions."
  sensitive   = true
  value       = local.team_admin_role_arn
}
