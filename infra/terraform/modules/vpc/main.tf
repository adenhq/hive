resource "aws_vpc" "hive_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  tags = {
    Name        = "${var.project_name}-vpc"
    ManagedBy   = "Terraform"
  }
}

resource "aws_subnet" "public_subnet" {
  vpc_id                  = aws_vpc.hive_vpc.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "${var.region}a"
  tags                    = { Name = "${var.project_name}-public" }
}
