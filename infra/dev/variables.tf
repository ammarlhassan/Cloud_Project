variable "aws_region" { type = string }
variable "environment" { type = string }

variable "public_subnets" { type = list(string) }
variable "private_subnets" { type = list(string) }

variable "db_instance_class" { type = string }
variable "db_allocated_storage" { type = number }
variable "db_username" { type = string }
variable "db_password" { type = string }
