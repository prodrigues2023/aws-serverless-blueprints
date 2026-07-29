"""The toy domain every blueprint's handler shares: an `orders` table with
a status a handler reads or transitions. One domain across all four
blueprints so a Milestone 4 resilience drill exercises the same shape
everywhere, not four unrelated toy problems.
"""
from decimal import Decimal
from typing import Any


def get_order(table, order_id: str) -> dict[str, Any] | None:
    response = table.get_item(Key={"orderId": order_id})
    return response.get("Item")


def update_order_status(table, order_id: str, status: str) -> None:
    table.update_item(
        Key={"orderId": order_id},
        UpdateExpression="SET #status = :status",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={":status": status},
    )


def seed_orders(table, orders: list[dict[str, Any]]) -> None:
    """Test-only convenience: load a fixed set of orders, converting any
    float amount to Decimal (see shared/idempotency.py's docstring for why
    DynamoDB needs that conversion)."""
    for order in orders:
        item = {**order}
        if "amount" in item and isinstance(item["amount"], float):
            item["amount"] = Decimal(str(item["amount"]))
        table.put_item(Item=item)
