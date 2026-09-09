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
