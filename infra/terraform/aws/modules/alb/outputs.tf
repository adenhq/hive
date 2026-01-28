output "alb_dns_name" {
  description = "ALB DNS name."
  value       = aws_lb.this.dns_name
}

output "alb_sg_id" {
  description = "Security group ID for the ALB."
  value       = aws_security_group.alb.id
}

output "target_group_arn" {
  description = "Target group ARN for the ECS service."
  value       = aws_lb_target_group.this.arn
}

output "listener_arn" {
  description = "ALB listener ARN."
  value       = aws_lb_listener.http.arn
}
