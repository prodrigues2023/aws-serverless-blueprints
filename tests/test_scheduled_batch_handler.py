import conftest  # noqa: F401
from scheduled_batch.handler import close_stale_orders
from shared import IdempotencyStore, seed_orders

SCHEDULE_NAME = "nightly-close"
FIRE_TIME = "2026-07-28T00:00:00Z"


def _seed(orders_table):
    seed_orders(
        orders_table,
        [
            {"orderId": "ORD-1", "amount": 10.0, "status": "delivered"},
            {"orderId": "ORD-2", "amount": 20.0, "status": "delivered"},
            {"orderId": "ORD-3", "amount": 30.0, "status": "in_transit"},
        ],
    )


def test_happy_path_closes_only_delivered_orders(orders_table, idempotency_table):
    _seed(orders_table)
    store = IdempotencyStore(idempotency_table)

    result = close_stale_orders(SCHEDULE_NAME, FIRE_TIME, orders_table, store)

    assert sorted(result["closedOrderIds"]) == ["ORD-1", "ORD-2"]
    assert orders_table.get_item(Key={"orderId": "ORD-3"})["Item"]["status"] == "in_transit"


def test_overlapping_run_for_the_same_scheduled_fire_time_processes_once(orders_table, idempotency_table):
    """scheduled-batch.md's stated failure mode: "a run that takes longer
    than the schedule interval can overlap the next one, double-processing
    unless guarded." Two invocations claiming the same scheduled fire time
    are the same logical run."""
    _seed(orders_table)
    store = IdempotencyStore(idempotency_table)

    first = close_stale_orders(SCHEDULE_NAME, FIRE_TIME, orders_table, store)
    second = close_stale_orders(SCHEDULE_NAME, FIRE_TIME, orders_table, store)

    assert first == second  # the second "run" returns the cached result, does not re-scan and re-close


def test_a_different_scheduled_fire_time_is_a_new_run(orders_table, idempotency_table):
    _seed(orders_table)
    store = IdempotencyStore(idempotency_table)

    close_stale_orders(SCHEDULE_NAME, FIRE_TIME, orders_table, store)
    # nothing left to close on the next run, but it must still be allowed
    # to attempt -- a distinct fire time is a distinct run, not deduped
    result = close_stale_orders(SCHEDULE_NAME, "2026-07-29T00:00:00Z", orders_table, store)

    assert result["closedOrderIds"] == []
