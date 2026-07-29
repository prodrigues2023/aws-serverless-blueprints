import json

import conftest  # noqa: F401
from shared import IdempotencyStore, seed_orders
from synchronous_api.handler import handle


def _seed(orders_table):
    seed_orders(orders_table, [{"orderId": "ORD-7", "amount": 24.99, "status": "delivered"}])


def test_get_existing_order(orders_table, idempotency_table):
    _seed(orders_table)
    store = IdempotencyStore(idempotency_table)
    event = {"httpMethod": "GET", "pathParameters": {"orderId": "ORD-7"}}

    response = handle(event, orders_table, store)

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["orderId"] == "ORD-7"


def test_get_missing_order_is_404(orders_table, idempotency_table):
    store = IdempotencyStore(idempotency_table)
    event = {"httpMethod": "GET", "pathParameters": {"orderId": "ORD-999"}}

    response = handle(event, orders_table, store)

    assert response["statusCode"] == 404


def test_post_refund_without_idempotency_key_is_rejected(orders_table, idempotency_table):
    _seed(orders_table)
    store = IdempotencyStore(idempotency_table)
    event = {"httpMethod": "POST", "pathParameters": {"orderId": "ORD-7"}, "headers": {}}

    response = handle(event, orders_table, store)

    assert response["statusCode"] == 400


def test_post_refund_happy_path(orders_table, idempotency_table):
    _seed(orders_table)
    store = IdempotencyStore(idempotency_table)
    event = {"httpMethod": "POST", "pathParameters": {"orderId": "ORD-7"}, "headers": {"Idempotency-Key": "client-key-1"}}

    response = handle(event, orders_table, store)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["status"] == "refunded"
    assert body["amountRefunded"] == 24.99


def test_duplicate_client_request_with_same_idempotency_key_returns_cached_result_once(orders_table, idempotency_table):
    """The exit criterion Milestone 3 actually cares about: a client
    retrying the same POST (same Idempotency-Key) after, say, a dropped
    response does not refund twice."""
    _seed(orders_table)
    store = IdempotencyStore(idempotency_table)
    event = {"httpMethod": "POST", "pathParameters": {"orderId": "ORD-7"}, "headers": {"Idempotency-Key": "client-key-2"}}

    first = handle(event, orders_table, store)
    second = handle(event, orders_table, store)

    assert json.loads(first["body"]) == json.loads(second["body"])
    order = orders_table.get_item(Key={"orderId": "ORD-7"})["Item"]
    assert order["status"] == "refunded"  # transitioned exactly once, not toggled or double-applied


def test_different_idempotency_keys_are_not_deduped_against_each_other(orders_table, idempotency_table):
    """Idempotency dedupes *redelivery of the same request* (ADR-0003), not
    two distinct client requests that happen to target the same order --
    that is a separate business rule (don't refund an already-refunded
    order) this handler does not implement, deliberately out of scope for
    a convention demo. This test documents the boundary rather than
    asserting the double-refund is correct."""
    _seed(orders_table)
    store = IdempotencyStore(idempotency_table)
    event_a = {"httpMethod": "POST", "pathParameters": {"orderId": "ORD-7"}, "headers": {"Idempotency-Key": "key-a"}}
    event_b = {"httpMethod": "POST", "pathParameters": {"orderId": "ORD-7"}, "headers": {"Idempotency-Key": "key-b"}}

    handle(event_a, orders_table, store)
    response_b = handle(event_b, orders_table, store)

    assert response_b["statusCode"] == 200  # key-b is its own delivery, not deduped against key-a's
