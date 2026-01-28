terraform {
  required_version = ">= 1.5.0"
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/ecs/${var.name_prefix}"
  retention_in_days = var.retention_in_days
}