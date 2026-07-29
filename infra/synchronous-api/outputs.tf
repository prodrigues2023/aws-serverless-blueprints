output "api_endpoint" {
  value = aws_apigatewayv2_stage.default.invoke_url
}

output "orders_table_name" {
  value = aws_dynamodb_table.orders.name
}
