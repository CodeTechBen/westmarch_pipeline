output "app_public_ip" {
  value = aws_eip.app.public_ip
}

output "app_url" {
  value = "http://${aws_eip.app.public_ip}"
}

output "db_private_ip" {
  value = aws_instance.db.private_ip
}

output "lambda_name" {
  value = aws_lambda_function.pipeline.function_name
}

output "scheduler_daily_name" {
  value = aws_scheduler_schedule.weekday_daily.name
}

output "scheduler_wednesday_name" {
  value = aws_scheduler_schedule.wednesday_every_3_hours.name
}