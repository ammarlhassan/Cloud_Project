provider "aws" {
  region = var.aws_region
}

# VPC
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  tags = { Name = "${var.environment}-vpc" }
}

# Subnets
resource "aws_subnet" "public" {
  count = 2
  vpc_id = aws_vpc.main.id
  cidr_block = var.public_subnets[count.index]
  map_public_ip_on_launch = true
}

resource "aws_subnet" "private" {
  count = 2
  vpc_id = aws_vpc.main.id
  cidr_block = var.private_subnets[count.index]
  map_public_ip_on_launch = false
}

# Example: S3 bucket
resource "aws_s3_bucket" "tts_bucket" {
  bucket = "tts-service-${var.environment}"
  acl    = "private"
  versioning { enabled = true }
  server_side_encryption_configuration {
    rule { apply_server_side_encryption_by_default { sse_algorithm = "AES256" } }
  }
}

# Example: RDS
resource "aws_db_instance" "user_db" {
  identifier = "${var.environment}-user-db"
  engine = "postgres"
  instance_class = var.db_instance_class
  allocated_storage = var.db_allocated_storage
  username = var.db_username
  password = var.db_password
  publicly_accessible = false
}
