import json

import conftest  # noqa: F401
from async_fanout.handler import handle
from shared import IdempotencyStore, seed_orders

VALID_EVENT_ID = "5e8b6e2a-6e33-4f9a-9c2e-2f6a1e9b6b3f"


def _sqs_record(message_id: str, event_id: str = VALID_EVENT_ID, order_id: str = "ORD-7") -> dict:
    return {
        "messageId": message_id,
        "body": json.dumps(
            {
                "eventId": event_id,
                "eventType": "order.refund_requested",
                "source": "orders-api",
                "occurredAt": "2026-07-28T14:03:00Z",
                "schemaVersion": "1",
                "data": {"orderId": order_id},
            }
        ),
    }


def _seed(orders_table):
    seed_orders(orders_table, [{"orderId": "ORD-7", "amount": 24.99, "status": "delivered"}])


def test_happy_path_processes_the_message_and_reports_no_failures(orders_table, idempotency_table):
    _seed(orders_table)
    store = IdempotencyStore(idempotency_table)
    event = {"Records": [_sqs_record("msg-1")]}

    result = handle(event, orders_table, store)

    assert result["batchItemFailures"] == []
    order = orders_table.get_item(Key={"orderId": "ORD-7"})["Item"]
    assert order["status"] == "refunded"


def test_redelivered_message_with_same_event_id_processes_once(orders_table, idempotency_table):
    """The blueprint's defining failure mode (async-fanout.md): the queue
    delivers at least once. Two SQS records with the same eventId (a
    genuine redelivery) must refund exactly once."""
    _seed(orders_table)
    store = IdempotencyStore(idempotency_table)

    handle({"Records": [_sqs_record("msg-1", event_id=VALID_EVENT_ID)]}, orders_table, store)
    result = handle({"Records": [_sqs_record("msg-1-redelivered", event_id=VALID_EVENT_ID)]}, orders_table, store)

    assert result["batchItemFailures"] == []  # the redelivery is a safe no-op, not a failure
    order = orders_table.get_item(Key={"orderId": "ORD-7"})["Item"]
    assert order["status"] == "refunded"


def test_malformed_envelope_is_reported_as_a_batch_item_failure(orders_table, idempotency_table):
    store = IdempotencyStore(idempotency_table)
    bad_record = {"messageId": "msg-bad", "body": json.dumps({"not": "a valid envelope"})}

    result = handle({"Records": [bad_record]}, orders_table, store)

    assert result["batchItemFailures"] == [{"itemIdentifier": "msg-bad"}]


def test_one_bad_record_does_not_block_a_good_record_in_the_same_batch(orders_table, idempotency_table):
    """Partial-batch-failure reporting: only the failing message is
    reported, so the queue's redrive policy retries -- and eventually
    dead-letters -- only the poison message, not its innocent batch-mates."""
    _seed(orders_table)
    store = IdempotencyStore(idempotency_table)
    bad_record = {"messageId": "msg-bad", "body": json.dumps({"not": "a valid envelope"})}
    good_record = _sqs_record("msg-good")

    result = handle({"Records": [bad_record, good_record]}, orders_table, store)

    assert result["batchItemFailures"] == [{"itemIdentifier": "msg-bad"}]
    order = orders_table.get_item(Key={"orderId": "ORD-7"})["Item"]
    assert order["status"] == "refunded"  # the good record still succeeded


def test_event_for_an_unknown_order_is_reported_as_a_failure_not_silently_dropped(orders_table, idempotency_table):
    store = IdempotencyStore(idempotency_table)
    record = _sqs_record("msg-1", order_id="ORD-does-not-exist")

    result = handle({"Records": [record]}, orders_table, store)

    assert result["batchItemFailures"] == [{"itemIdentifier": "msg-1"}]
