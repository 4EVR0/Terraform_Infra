provider "aws" {
  region              = var.aws_region
  allowed_account_ids = [var.aws_account_id]
  # Existing tags must be inventoried before adding default_tags.
}
