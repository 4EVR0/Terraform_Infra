# Adopt only the existing monitoring instance; apply after PR review and a fresh plan.
import {
  to = aws_instance.monitoring
  id = var.instance_ids["monitoring"]
}
