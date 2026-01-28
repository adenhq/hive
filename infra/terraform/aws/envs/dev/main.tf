terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project = "hive"
      Env     = "dev"
    }
  }
}

module "iam" {
  source               = "../../modules/iam"
  name_prefix          = var.name_prefix
  secrets_manager_arns = [for s in var.secrets : s.arn]
}

module "observability" {
  source            = "../../modules/observability"
  name_prefix       = var.name_prefix
  retention_in_days = var.log_retention_days
}

module "alb" {
  source            = "../../modules/alb"
  name_prefix       = var.name_prefix
  vpc_id            = var.vpc_id
  public_subnet_ids = var.public_subnet_ids
  container_port    = var.container_port
  health_check_path = var.health_check_path
}

module "ecs" {
  source                  = "../../modules/ecs"
  name_prefix             = var.name_prefix
  aws_region              = var.aws_region
  vpc_id                  = var.vpc_id
  private_subnet_ids      = var.private_subnet_ids
  container_port          = var.container_port
  image                   = var.image
  cpu                     = var.cpu
  memory                  = var.memory
  desired_count           = var.desired_count
  env_vars                = var.env_vars
  secrets                 = var.secrets
  task_execution_role_arn = module.iam.task_execution_role_arn
  task_role_arn           = module.iam.task_role_arn
  log_group_name          = module.observability.log_group_name
  target_group_arn        = module.alb.target_group_arn
  alb_sg_id               = module.alb.alb_sg_id
  listener_arn            = module.alb.listener_arn
}