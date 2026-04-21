terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

# ============================
# Networking
# ============================
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public"
  }
}

resource "aws_subnet" "private_app_data" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_data_subnet_cidr
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "${var.project_name}-private-data"
  }
}

resource "aws_subnet" "private_lambda" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_lambda_subnet_cidr
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "${var.project_name}-private-lambda"
  }
}

# Public route table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

resource "aws_route" "public_default" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

resource "aws_route_table_association" "public_assoc" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# Private route table (to NAT instance)
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-private-rt"
  }
}

# route to NAT instance added after NAT instance creation
resource "aws_route_table_association" "private_data_assoc" {
  subnet_id      = aws_subnet.private_app_data.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_lambda_assoc" {
  subnet_id      = aws_subnet.private_lambda.id
  route_table_id = aws_route_table.private.id
}

# ============================
# Security Groups
# ============================
resource "aws_security_group" "app" {
  name        = "${var.project_name}-app-sg"
  description = "Public access to Flask app"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_http_cidrs
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_http_cidrs
  }

  ingress {
    description = "SSH from admin IPs"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidrs
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-app-sg"
  }
}

resource "aws_security_group" "db" {
  name        = "${var.project_name}-db-sg"
  description = "Postgres only from app and lambda"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Postgres from app EC2"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  ingress {
    description     = "Postgres from Lambda"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }

  ingress {
    description = "SSH from admin IPs"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidrs
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-db-sg"
  }
}

resource "aws_security_group" "lambda" {
  name        = "${var.project_name}-lambda-sg"
  description = "Lambda access to DB and internet through NAT instance"
  vpc_id      = aws_vpc.main.id

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-lambda-sg"
  }
}

resource "aws_security_group" "nat" {
  name        = "${var.project_name}-nat-sg"
  description = "NAT instance SG"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "Private subnet traffic for NAT"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [
      var.private_data_subnet_cidr,
      var.private_lambda_subnet_cidr
    ]
  }

  ingress {
    description = "SSH from admin IPs"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidrs
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-nat-sg"
  }
}

# ============================
# Key pair
# ============================
resource "aws_key_pair" "main" {
  key_name   = "${var.project_name}-key"
  public_key = var.ssh_public_key
}

# ============================
# NAT instance
# ============================
resource "aws_instance" "nat" {
  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = var.nat_instance_type
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.nat.id]
  key_name                    = aws_key_pair.main.key_name
  associate_public_ip_address = true
  source_dest_check           = false

  user_data = templatefile("${path.module}/user_data_nat.sh.tpl", {})

  tags = {
    Name = "${var.project_name}-nat"
  }
}

resource "aws_route" "private_default" {
  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  network_interface_id   = aws_instance.nat.primary_network_interface_id

  depends_on = [aws_instance.nat]
}


# ============================
# DB EC2 (private)
# ============================
resource "aws_instance" "db" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.db_instance_type
  subnet_id              = aws_subnet.private_app_data.id
  vpc_security_group_ids = [aws_security_group.db.id]
  key_name               = aws_key_pair.main.key_name

  associate_public_ip_address = false

  root_block_device {
    volume_size = var.db_root_volume_size
    volume_type = "gp3"
  }

  user_data = templatefile("${path.module}/user_data_db.sh.tpl", {
    db_name     = var.db_name
    db_username = var.db_username
    db_password = var.db_password
    app_cidr    = var.public_subnet_cidr
    lambda_cidr = var.private_lambda_subnet_cidr
  })

  tags = {
    Name = "${var.project_name}-db"
  }
}

# ============================
# App EC2 (public Flask)
# ============================
resource "aws_instance" "app" {
  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = var.app_instance_type
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.app.id]
  key_name                    = aws_key_pair.main.key_name
  associate_public_ip_address = true

  root_block_device {
    volume_size = var.app_root_volume_size
    volume_type = "gp3"
  }

  user_data = templatefile("${path.module}/user_data_app.sh.tpl", {
    db_host     = aws_instance.db.private_ip
    db_name     = var.db_name
    db_username = var.db_username
    db_password = var.db_password
    flask_port  = var.flask_port
  })

  depends_on = [aws_instance.db]

  tags = {
    Name = "${var.project_name}-app"
  }
}

resource "aws_eip" "app" {
  domain = "vpc"

  tags = {
    Name = "${var.project_name}-app-eip"
  }
}

resource "aws_eip_association" "app" {
  instance_id   = aws_instance.app.id
  allocation_id = aws_eip.app.id
}

# ============================
# Lambda IAM
# ============================
resource "aws_iam_role" "lambda_exec" {
  name = "${var.project_name}-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_logs" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_vpc_access" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# ============================
# Lambda (container image)
# ============================
resource "aws_lambda_function" "pipeline" {
  function_name = "${var.project_name}-pipeline"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = var.lambda_image_uri
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size

  environment {
    variables = {
      DB_HOST     = aws_instance.db.private_ip
      DB_NAME     = var.db_name
      DB_USER     = var.db_username
      DB_PASSWORD = var.db_password
      WESTMARCH_URL = var.westmarch_url
      WESTMARCH_ADVENTURES_URL=var.westmarch_adventures_url
      DND_BEYOND_API=var.dnd_beyond_api
      }
  }

  vpc_config {
    subnet_ids = [aws_subnet.private_lambda.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_logs,
    aws_iam_role_policy_attachment.lambda_vpc_access
  ]
}

# ============================
# Scheduler IAM
# ============================
resource "aws_iam_role" "scheduler_exec" {
  name = "${var.project_name}-scheduler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "scheduler.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_policy" "scheduler_invoke_lambda" {
  name = "${var.project_name}-scheduler-invoke-lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = aws_lambda_function.pipeline.arn
    }]
  })
}

resource "aws_iam_role_policy_attachment" "scheduler_invoke_attach" {
  role       = aws_iam_role.scheduler_exec.name
  policy_arn = aws_iam_policy.scheduler_invoke_lambda.arn
}

# ============================
# EventBridge Scheduler
# ============================
resource "aws_scheduler_schedule" "weekday_daily" {
  name                         = "${var.project_name}-weekday-daily"
  group_name                   = "default"
  schedule_expression          = "cron(0 ${var.daily_run_hour} ? * MON,TUE,THU,FRI *)"
  schedule_expression_timezone = var.scheduler_timezone
  state                        = "ENABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.pipeline.arn
    role_arn = aws_iam_role.scheduler_exec.arn

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }
}

resource "aws_scheduler_schedule" "wednesday_every_3_hours" {
  name                         = "${var.project_name}-wednesday-every-3-hours"
  group_name                   = "default"
  schedule_expression          = "cron(0 0/3 ? * WED *)"
  schedule_expression_timezone = var.scheduler_timezone
  state                        = "ENABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.pipeline.arn
    role_arn = aws_iam_role.scheduler_exec.arn

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }
}