# Read-only kickoff: these data sources do not adopt or modify resources.
data "aws_vpc" "existing" {
  id = var.vpc_id
}

data "aws_instance" "existing" {
  for_each    = var.instance_ids
  instance_id = each.value
}

output "existing_instances" {
  sensitive   = true
  description = "Observed AWS instances; this output does not mean Terraform manages them."
  value = {
    for name, instance in data.aws_instance.existing : name => {
      id            = instance.id
      instance_type = instance.instance_type
      subnet_id     = instance.subnet_id
    }
  }
}
