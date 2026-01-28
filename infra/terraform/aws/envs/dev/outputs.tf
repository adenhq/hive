output "alb_url" {
  description = "HTTP URL for the ALB."
  value       = "http://${module.alb.alb_dns_name}"
}

output "ecs_cluster_name" {
  description = "ECS cluster name."
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "ECS service name."
  value       = module.ecs.service_name
}