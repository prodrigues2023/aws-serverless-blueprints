"""The idempotency convention (docs/contracts/idempotency-convention.md),
made runnable: a DynamoDB-backed dedupe record and the conditional-write
sequence that makes it correct under concurrent redelivery, not just under
a later, sequential retry.

Every field name and the four-step handler sequence below match the
contract doc exactly -- this module is the convention made executable, not
a reinterpretation of it.
"""
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

from botocore.exceptions import ClientError

RETENTION_SECONDS = 7 * 24 * 60 * 60  # 7 days, per idempotency-convention.md's provisional window


def _to_dynamodb_safe(value: Any) -> Any:
    """DynamoDB's attribute types have no native float -- a `result` dict
    with a plain float (a dollar amount, typically) fails at write time,
    not at review time, which is exactly the kind of thing this shared
    module exists to get right once rather than leaving every handler to
    discover it independently. Recurses through dicts and lists; leaves
    everything else as-is.
    """
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: _to_dynamodb_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_dynamodb_safe(v) for v in value]
    return value


def _from_dynamodb_safe(value: Any) -> Any:
    """The inverse of `_to_dynamodb_safe`, applied when handing a cached
    result back to a handler -- callers should not need to know their
    result was round-tripped through Decimal."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: _from_dynamodb_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_from_dynamodb_safe(v) for v in value]
    return value


class IdempotencyAction(str, Enum):
    PROCEED = "proceed"  # no prior record -- do the work
    RETURN_CACHED = "return_cached"  # status: completed -- safe no-op, return the cached result
    RETRY_LATER = "retry_later"  # status: in_progress -- the concurrent-delivery race; back off
    NEEDS_DECISION = "needs_decision"  # status: failed -- per-handler decision, not prescribed here


@dataclass
class IdempotencyOutcome:
    action: IdempotencyAction
    cached_result: dict[str, Any] | None = None


class IdempotencyStore:
    """Wraps one DynamoDB table shaped per idempotency-convention.md's
    dedupe-record fields: idempotencyKey, status, result, expiresAt,
    createdAt.
    """

    def __init__(self, table, clock=time.time):
        self.table = table
        self.clock = clock

    def begin(self, idempotency_key: str) -> IdempotencyOutcome:
        """Step 1 of the handler sequence: conditional write claiming this
        key. This is what closes the concurrent-delivery race -- two
        callers racing here, only one wins the conditional put.
        """
        now = self.clock()
        try:
            self.table.put_item(
                Item={
                    "idempotencyKey": idempotency_key,
                    "status": "in_progress",
                    "result": None,
                    "expiresAt": int(now) + RETENTION_SECONDS,
                    "createdAt": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
                },
                ConditionExpression="attribute_not_exists(idempotencyKey)",
            )
            return IdempotencyOutcome(action=IdempotencyAction.PROCEED)
        except ClientError as e:
            if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise
            return self._resolve_existing(idempotency_key)

    def _resolve_existing(self, idempotency_key: str) -> IdempotencyOutcome:
        """Step 4: someone else's `begin()` won the race. Read what they
        left and decide accordingly."""
        existing = self.table.get_item(Key={"idempotencyKey": idempotency_key}).get("Item")
        if existing is None:
            # The record existed a moment ago (we lost the conditional put)
            # but is gone now -- DynamoDB TTL deletion is not instantaneous
            # with the conditional check, so this is a legitimate, if rare,
            # window. Treat it the same as a concurrent in-flight delivery:
            # back off rather than silently proceeding as if we were first.
            return IdempotencyOutcome(action=IdempotencyAction.RETRY_LATER)

        status = existing["status"]
        if status == "completed":
            return IdempotencyOutcome(action=IdempotencyAction.RETURN_CACHED, cached_result=_from_dynamodb_safe(existing.get("result")))
        if status == "in_progress":
            return IdempotencyOutcome(action=IdempotencyAction.RETRY_LATER)
        return IdempotencyOutcome(action=IdempotencyAction.NEEDS_DECISION)  # status == "failed"

    def complete(self, idempotency_key: str, result: dict[str, Any]) -> None:
        """Step 3: the side effect succeeded -- record the outcome so a
        future duplicate returns it instead of recomputing."""
        self.table.update_item(
            Key={"idempotencyKey": idempotency_key},
            UpdateExpression="SET #status = :completed, #result = :result",
            ExpressionAttributeNames={"#status": "status", "#result": "result"},
            ExpressionAttributeValues={":completed": "completed", ":result": _to_dynamodb_safe(result)},
        )

    def mark_failed(self, idempotency_key: str) -> None:
        """The side effect did not complete successfully. Left as
        `failed` for the next delivery's per-handler decision
        (idempotency-convention.md step 4's third bullet) -- this module
        does not decide whether a failed attempt should be retried
        immediately."""
        self.table.update_item(
            Key={"idempotencyKey": idempotency_key},
            UpdateExpression="SET #status = :failed",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":failed": "failed"},
        )


def run_idempotently(store: IdempotencyStore, idempotency_key: str, work) -> dict[str, Any]:
    """The full handler sequence in one call for the common case: run
    `work()` at most once per `idempotency_key`, returning the cached
    result on a duplicate. Raises `RetryLaterError` for the concurrent-
    delivery race and `NeedsDecisionError` for a previously-failed
    attempt, rather than silently picking a policy for either -- both are
    the caller's decision per the contract.
    """
    outcome = store.begin(idempotency_key)

    if outcome.action == IdempotencyAction.RETURN_CACHED:
        return outcome.cached_result or {}

    if outcome.action == IdempotencyAction.RETRY_LATER:
        raise RetryLaterError(idempotency_key)

    if outcome.action == IdempotencyAction.NEEDS_DECISION:
        raise NeedsDecisionError(idempotency_key)

    try:
        result = work()
    except Exception:
        store.mark_failed(idempotency_key)
        raise
    store.complete(idempotency_key, result)
    return result


class RetryLaterError(Exception):
    """A concurrent delivery of the same idempotency key is already
    in_progress. The caller should back off and let the queue redeliver,
    or retry after a short delay -- never proceed with the side effect."""

    def __init__(self, idempotency_key: str):
        super().__init__(f"delivery for '{idempotency_key}' is already in_progress elsewhere; retry later")
        self.idempotency_key = idempotency_key


class NeedsDecisionError(Exception):
    """A previous attempt for this key failed. Whether to retry now is a
    per-handler decision (idempotency-convention.md step 4) -- this
    module does not make it silently."""

    def __init__(self, idempotency_key: str):
        super().__init__(f"a previous attempt for '{idempotency_key}' failed; caller must decide whether to retry")
        self.idempotency_key = idempotency_key
