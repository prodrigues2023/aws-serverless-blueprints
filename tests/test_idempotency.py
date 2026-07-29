"""Exercises docs/contracts/idempotency-convention.md's handler sequence
against a real (moto-mocked) DynamoDB table -- including the
concurrent-delivery race the convention exists to close, not just the
easy sequential-retry case.
"""
import conftest  # noqa: F401
import pytest
from shared.idempotency import (
    IdempotencyAction,
    IdempotencyStore,
    NeedsDecisionError,
    RetryLaterError,
    run_idempotently,
)


def test_first_delivery_proceeds(idempotency_table):
    store = IdempotencyStore(idempotency_table)
    outcome = store.begin("evt-1")
    assert outcome.action == IdempotencyAction.PROCEED


def test_completed_delivery_is_returned_as_cached_not_reprocessed(idempotency_table):
    store = IdempotencyStore(idempotency_table)
    calls = []

    def work():
        calls.append(1)
        return {"refunded": True, "amount": 24.99}

    first = run_idempotently(store, "evt-2", work)
    second = run_idempotently(store, "evt-2", work)

    assert first == {"refunded": True, "amount": 24.99}
    assert second == first
    assert len(calls) == 1  # the side effect ran exactly once


def test_concurrent_in_progress_delivery_raises_retry_later_not_proceed(idempotency_table):
    """The race idempotency-convention.md's conditional write exists to
    close: a second delivery arrives while the first is still mid-flight
    (status still in_progress, no result yet). It must not proceed with
    the side effect a second time just because completion hasn't been
    confirmed."""
    store = IdempotencyStore(idempotency_table)
    first_outcome = store.begin("evt-3")
    assert first_outcome.action == IdempotencyAction.PROCEED
    # first delivery has not called complete() yet -- still in_progress

    second_outcome = store.begin("evt-3")
    assert second_outcome.action == IdempotencyAction.RETRY_LATER

    with pytest.raises(RetryLaterError):
        run_idempotently(store, "evt-3", lambda: pytest.fail("must not run while another delivery is in_progress"))


def test_failed_attempt_requires_a_caller_decision_not_silent_retry(idempotency_table):
    store = IdempotencyStore(idempotency_table)

    def failing_work():
        raise RuntimeError("downstream unavailable")

    with pytest.raises(RuntimeError):
        run_idempotently(store, "evt-4", failing_work)

    # a second delivery for the same key must not silently retry --
    # idempotency-convention.md leaves that decision to the caller
    with pytest.raises(NeedsDecisionError):
        run_idempotently(store, "evt-4", lambda: {"ok": True})


def test_two_different_keys_both_proceed_independently(idempotency_table):
    store = IdempotencyStore(idempotency_table)
    assert store.begin("evt-5").action == IdempotencyAction.PROCEED
    assert store.begin("evt-6").action == IdempotencyAction.PROCEED


def test_dedupe_record_carries_a_ttl_within_the_documented_retention_window(idempotency_table):
    import time

    store = IdempotencyStore(idempotency_table)
    before = int(time.time())
    store.begin("evt-7")
    item = idempotency_table.get_item(Key={"idempotencyKey": "evt-7"})["Item"]
    seven_days = 7 * 24 * 60 * 60
    assert before + seven_days <= item["expiresAt"] <= before + seven_days + 5
