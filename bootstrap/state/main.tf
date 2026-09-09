provider "aws" {
  region              = var.aws_region
  allowed_account_ids = [var.aws_account_id]
}

data "aws_partition" "current" {}

resource "aws_s3_bucket" "state" {
  bucket        = var.state_bucket_name
  force_destroy = false
  tags = {
    Project   = "4EVR0"
    Purpose   = "terraform-state"
    ManagedBy = "Terraform"
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_policy" "state" {
  bucket = aws_s3_bucket.state.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [local.bucket_arn, "${local.bucket_arn}/*"]
      Condition = {
        Bool = {
          "aws:SecureTransport"       = "false"
          "aws:PrincipalIsAWSService" = "false"
        }
      }
    }]
  })
  depends_on = [aws_s3_bucket_public_access_block.state]
}

locals {
  bucket_arn = "arn:${data.aws_partition.current.partition}:s3:::${var.state_bucket_name}"
  state_keys = {
    bootstrap = "4evr0/bootstrap/terraform.tfstate"
    project   = "4evr0/project/terraform.tfstate"
  }
  # Templates only: no IAM principal receives these permissions automatically.
  backend_policies = {
    for scope, key in local.state_keys : scope => jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Sid      = "ListStateBucket"
          Effect   = "Allow"
          Action   = ["s3:ListBucket"]
          Resource = local.bucket_arn
        },
        {
          Sid      = "ReadWriteState"
          Effect   = "Allow"
          Action   = ["s3:GetObject", "s3:PutObject"]
          Resource = "${local.bucket_arn}/${key}"
        },
        {
          Sid      = "ManageStateLock"
          Effect   = "Allow"
          Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
          Resource = "${local.bucket_arn}/${key}.tflock"
        }
      ]
    })
  }
}
