provider "aws" {
  region = "us-east-1"
}

module "network" {
  source       = "./modules/vpc"
  project_name = "aden-hive-prod"
  region       = "us-east-1"
}

output "vpc_id" {
  value = module.network.vpc_id
}
