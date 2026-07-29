# docs/contracts/idempotency-convention.md's dedupe record, as a table:
# idempotencyKey (partition key), status, result, expiresAt (TTL),
# createdAt. On-demand billing -- this table's traffic mirrors whatever
# invokes the handler, and provisioning fixed capacity for it is exactly
# the kind of premature tuning the catalogue's key constraints (docs/context.md)
# say not to spend effort on.

resource "aws_dynamodb_table" "this" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "idempotencyKey"

  attribute {
    name = "idempotencyKey"
    type = "S"
  }

  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }

  tags = var.tags
}
