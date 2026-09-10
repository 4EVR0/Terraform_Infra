variable "monitoring_s3" {
  description = "Reviewed existing S3 bucket used by monitoring. Keep the actual bucket name and tags in ignored local tfvars."
  type = object({
    bucket_name = string
    tags        = optional(map(string))
  })
  nullable = false

  validation {
    condition     = length(trimspace(var.monitoring_s3.bucket_name)) > 0
    error_message = "The monitoring S3 bucket name must not be empty."
  }
}
