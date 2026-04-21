variable "aws_region" {
  type    = string
  default = "eu-west-2"
}

variable "project_name" {
  type    = string
  default = "tavern-dashboard"
}

variable "vpc_cidr" {
  type    = string
  default = "10.60.0.0/16"
}

variable "public_subnet_cidr" {
  type    = string
  default = "10.60.1.0/24"
}

variable "private_data_subnet_cidr" {
  type    = string
  default = "10.60.2.0/24"
}

variable "private_lambda_subnet_cidr" {
  type    = string
  default = "10.60.3.0/24"
}

variable "app_instance_type" {
  type    = string
  default = "t3.micro"
}

variable "db_instance_type" {
  type    = string
  default = "t3.micro"
}

variable "nat_instance_type" {
  type    = string
  default = "t3.nano"
}

variable "app_root_volume_size" {
  type    = number
  default = 30
}

variable "db_root_volume_size" {
  type    = number
  default = 30
}

variable "ssh_public_key" {
  type = string
}

variable "allowed_ssh_cidrs" {
  type = list(string)
}

variable "allowed_http_cidrs" {
  type    = list(string)
  default = ["0.0.0.0/0"]
}

variable "flask_port" {
  type    = number
  default = 8000
}

variable "db_name" {
  type    = string
  default = "tavern"
}

variable "db_username" {
  type    = string
  default = "tavern_admin"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "lambda_image_uri" {
  type = string
}

variable "lambda_timeout" {
  type    = number
  default = 900
}

variable "lambda_memory_size" {
  type    = number
  default = 2048
}

variable "scheduler_timezone" {
  type    = string
  default = "Europe/London"
}

variable "daily_run_hour" {
  type    = number
  default = 9
}

variable "westmarch_url" {
  type = string
}

variable "westmarch_adventures_url" {
  type = string
}

variable "dnd_beyond_api" {
  type = string
}

variable "domain_name" {
  type = string
}

variable "admin_email" {
  type = string
}

variable "route53_zone_id" {
  type = string
}