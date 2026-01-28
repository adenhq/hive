output "cluster_name" {
  description = "ECS cluster name."
  value       = aws_ecs_cluster.this.name
}

output "service_name" {
  description = "ECS service name."
  value       = aws_ecs_service.this.name
}

output "task_security_group_id" {
  description = "Security group ID for the ECS service."
  value       = aws_security_group.ecs.id
}

