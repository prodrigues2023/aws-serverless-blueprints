"""Asynchronous fan-out blueprint (docs/blueprints/async-fanout.md): SQS
-> this Lambda -> the orders table, idempotent on each event's `eventId`
(event-convention.md), with a dead-letter queue on the source queue
catching whatever fails repeatedly (dead-letter-convention.md).

Uses SQS's partial-batch-failure reporting (`batchItemFailures`): one bad
message in a batch does not force the whole batch to be retried -- only
the messages that actually failed are returned to the queue, which is
what makes the per-message retry count in the dead-letter convention mean
what it says.
"""
import json
import os
from decimal import Decimal
from typing import Any

import boto3
from shared import (
    IdempotencyStore,
    InvalidEventError,
    NeedsDecisionError,
    RetryLaterError,
    get_order,
    parse_event,
    run_idempotently,
    update_order_status,
)


def _process_record(record: dict[str, Any], orders_table, idempotency_store: IdempotencyStore) -> None:
    raw = json.loads(record["body"])
    event = parse_event(raw)  # raises InvalidEventError on a malformed envelope -- not retried, see below

    if event.event_type != "order.refund_requested":
        return  # not this consumer's concern; a real deployment would filter at the source, this is defence in depth

    order_id = event.data["orderId"]
    order = get_order(orders_table, order_id)
    if order is None:
        raise ValueError(f"no such order '{order_id}' for event {event.event_id}")

    def do_refund() -> dict[str, Any]:
        update_order_status(orders_table, order_id, "refunded")
        amount = order["amount"]
        return {"orderId": order_id, "status": "refunded", "amountRefunded": float(amount) if isinstance(amount, Decimal) else amount}

    run_idempotently(idempotency_store, event.idempotency_key, do_refund)


def handle(event: dict[str, Any], orders_table, idempotency_store: IdempotencyStore) -> dict[str, Any]:
    """Returns the `batchItemFailures` shape SQS's Lambda event source
    mapping expects: only the records that actually failed are named, so
    only they are redelivered."""
    failures = []
    for record in event.get("Records", []):
        try:
            _process_record(record, orders_table, idempotency_store)
        except InvalidEventError:
            # A malformed envelope will never parse correctly no matter
            # how many times it's redelivered -- still reported as a
            # failure so the dead-letter convention's retry count and
            # eventual DLQ placement applies to it like any other failure,
            # rather than being silently swallowed here.
            failures.append(record["messageId"])
        except RetryLaterError:
            # A concurrent delivery is already in_progress -- back off by
            # reporting this one as failed so SQS redelivers it later,
            # rather than proceeding with a second side effect.
            failures.append(record["messageId"])
        except NeedsDecisionError:
            # A previous attempt failed; this consumer's policy is to
            # retry (which will re-run mark_failed on repeated failure,
            # same as any other exception) rather than requiring a human
            # unblock -- a stricter consumer could choose to always report
            # failure here and let the DLQ hold it for inspection instead.
            failures.append(record["messageId"])
        except Exception:  # noqa: BLE001 -- any other handler failure also redelivers, same as SQS's default
            failures.append(record["messageId"])

    return {"batchItemFailures": [{"itemIdentifier": message_id} for message_id in failures]}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # pragma: no cover -- thin AWS wiring
    orders_table = boto3.resource("dynamodb").Table(os.environ["ORDERS_TABLE_NAME"])
    idempotency_table = boto3.resource("dynamodb").Table(os.environ["IDEMPOTENCY_TABLE_NAME"])
    return handle(event, orders_table, IdempotencyStore(idempotency_table))
