"""Scheduled/batch blueprint (docs/blueprints/scheduled-batch.md):
EventBridge Scheduler -> this Lambda -> iterate the orders table on a
cadence. Idempotent on the *run*, not on an incoming event -- there is no
producer-assigned eventId for a scheduled trigger
(event-convention.md's "fields that do not apply" note), so the
idempotency key is `{scheduleName}:{scheduledFireTime}`
(idempotency-convention.md's "scheduled/batch: run identity" note),
guarding against the blueprint's stated "overlapping runs" failure mode.

This toy dataset is small enough to process in one invocation. A dataset
too large for one invocation's timeout fans out to the
[async fan-out](../async_fanout/handler.py) blueprint per
scheduled-batch.md's own "when not to use" clause -- not implemented here,
since that is exactly the async-fanout blueprint this one already has.
"""
import os
from typing import Any

import boto3
from shared import IdempotencyStore, run_idempotently, scheduled_run_key


def close_stale_orders(schedule_name: str, scheduled_fire_time: str, orders_table, idempotency_store: IdempotencyStore) -> dict[str, Any]:
    run_key = scheduled_run_key(schedule_name, scheduled_fire_time)

    def run_batch() -> dict[str, Any]:
        closed = []
        response = orders_table.scan()
        for order in response.get("Items", []):
            if order.get("status") == "delivered":
                orders_table.update_item(
                    Key={"orderId": order["orderId"]},
                    UpdateExpression="SET #status = :status",
                    ExpressionAttributeNames={"#status": "status"},
                    ExpressionAttributeValues={":status": "closed"},
                )
                closed.append(order["orderId"])
        return {"closedOrderIds": closed, "count": len(closed)}

    return run_idempotently(idempotency_store, run_key, run_batch)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # pragma: no cover -- thin AWS wiring
    orders_table = boto3.resource("dynamodb").Table(os.environ["ORDERS_TABLE_NAME"])
    idempotency_table = boto3.resource("dynamodb").Table(os.environ["IDEMPOTENCY_TABLE_NAME"])
    schedule_name = os.environ["SCHEDULE_NAME"]
    # EventBridge Scheduler is configured to pass its own intended fire
    # time in the input per idempotency-convention.md's note that this
    # must be the *scheduled* time, not the actual invocation time.
    scheduled_fire_time = event["scheduledFireTime"]
    return close_stale_orders(schedule_name, scheduled_fire_time, orders_table, IdempotencyStore(idempotency_table))
