resource "aws_s3_bucket" "monitoring" {
  bucket        = var.monitoring_s3.bucket_name
  force_destroy = false
  tags          = var.monitoring_s3.tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "monitoring" {
  bucket = aws_s3_bucket.monitoring.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_public_access_block" "monitoring" {
  bucket = aws_s3_bucket.monitoring.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_ownership_controls" "monitoring" {
  bucket = aws_s3_bucket.monitoring.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }

  lifecycle {
    prevent_destroy = true
  }
}

import {
  to = aws_s3_bucket.monitoring
  id = var.monitoring_s3.bucket_name
}

import {
  to = aws_s3_bucket_server_side_encryption_configuration.monitoring
  id = var.monitoring_s3.bucket_name
}

import {
  to = aws_s3_bucket_public_access_block.monitoring
  id = var.monitoring_s3.bucket_name
}

import {
  to = aws_s3_bucket_ownership_controls.monitoring
  id = var.monitoring_s3.bucket_name
}
