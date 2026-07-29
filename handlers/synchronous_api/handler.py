"""Synchronous API blueprint (docs/blueprints/synchronous-api.md): API
Gateway -> this Lambda -> the orders table, reading and writing
synchronously. `handle()` is the testable core; `lambda_handler()` is the
thin AWS-wiring entrypoint real deployment uses.

Two routes: `GET /orders/{orderId}` (read, no idempotency concern) and
`POST /orders/{orderId}/refund` (write, idempotent on the client's
`Idempotency-Key` header per event-convention.md's API Gateway note --
there is no upstream producer assigning an eventId here, the client is
the producer).
"""
import json
import os
from decimal import Decimal
from typing import Any

import boto3
from shared import (
    IdempotencyStore,
    NeedsDecisionError,
    RetryLaterError,
    get_order,
    idempotency_key_from_api_request,
    run_idempotently,
    update_order_status,
)


def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {"statusCode": status_code, "headers": {"Content-Type": "application/json"}, "body": json.dumps(body, default=str)}


def handle(event: dict[str, Any], orders_table, idempotency_store: IdempotencyStore) -> dict[str, Any]:
    method = event.get("httpMethod")
    order_id = (event.get("pathParameters") or {}).get("orderId")
    if not order_id:
        return _response(400, {"error": "orderId path parameter is required"})

    if method == "GET":
        order = get_order(orders_table, order_id)
        if order is None:
            return _response(404, {"error": f"no such order '{order_id}'"})
        return _response(200, order)

    if method == "POST":
        idempotency_key = idempotency_key_from_api_request(event.get("headers") or {})
        if idempotency_key is None:
            return _response(400, {"error": "POST /orders/{orderId}/refund requires an Idempotency-Key header"})

        order = get_order(orders_table, order_id)
        if order is None:
            return _response(404, {"error": f"no such order '{order_id}'"})

        def do_refund() -> dict[str, Any]:
            update_order_status(orders_table, order_id, "refunded")
            amount = order["amount"]
            return {"orderId": order_id, "status": "refunded", "amountRefunded": float(amount) if isinstance(amount, Decimal) else amount}

        try:
            result = run_idempotently(idempotency_store, idempotency_key, do_refund)
        except RetryLaterError:
            return _response(409, {"error": "a request with this Idempotency-Key is already in progress"})
        except NeedsDecisionError:
            return _response(500, {"error": "a previous request with this Idempotency-Key failed; contact support before retrying"})
        return _response(200, result)

    return _response(405, {"error": f"unsupported method '{method}'"})


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # pragma: no cover -- thin AWS wiring
    orders_table = boto3.resource("dynamodb").Table(os.environ["ORDERS_TABLE_NAME"])
    idempotency_table = boto3.resource("dynamodb").Table(os.environ["IDEMPOTENCY_TABLE_NAME"])
    return handle(event, orders_table, IdempotencyStore(idempotency_table))
