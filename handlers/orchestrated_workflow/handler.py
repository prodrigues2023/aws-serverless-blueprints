"""Orchestrated workflow blueprint (docs/blueprints/orchestrated-workflow.md):
a Step Functions state machine holds the process state
(docs/adr/0002-stateless-ephemeral.md's "stateless functions, stateful
orchestrator"); each step below is one stateless Lambda. Step Functions
retries a failed step on its own schedule, so each step is idempotent --
keyed on `{executionId}:{stepName}` (idempotency-convention.md's general
shape, applied per step rather than per top-level event since a workflow
execution has no single incoming event envelope).

Three steps, three entrypoints in one module (each maps to its own Lambda
function in the Terraform config): validate -> process -> notify. State
flows from one step's output to the next step's input, exactly as
Step Functions passes it.
"""
import os
from decimal import Decimal
from typing import Any

import boto3
from shared import (
    IdempotencyStore,
    get_order,
    run_idempotently,
    update_order_status,
)


def _step_key(execution_id: str, step_name: str) -> str:
    return f"{execution_id}:{step_name}"


def validate(input_state: dict[str, Any], orders_table, idempotency_store: IdempotencyStore) -> dict[str, Any]:
    order_id = input_state["orderId"]
    execution_id = input_state["executionId"]

    def check() -> dict[str, Any]:
        order = get_order(orders_table, order_id)
        eligible = order is not None and order.get("status") != "refunded"
        return {"eligible": eligible}

    result = run_idempotently(idempotency_store, _step_key(execution_id, "validate"), check)
    return {**input_state, "eligible": result["eligible"]}


def process(input_state: dict[str, Any], orders_table, idempotency_store: IdempotencyStore) -> dict[str, Any]:
    order_id = input_state["orderId"]
    execution_id = input_state["executionId"]

    if not input_state.get("eligible"):
        return {**input_state, "refunded": False}

    def do_refund() -> dict[str, Any]:
        order = get_order(orders_table, order_id)
        update_order_status(orders_table, order_id, "refunded")
        amount = order["amount"]
        return {"refunded": True, "amountRefunded": float(amount) if isinstance(amount, Decimal) else amount}

    result = run_idempotently(idempotency_store, _step_key(execution_id, "process"), do_refund)
    return {**input_state, **result}


def notify(input_state: dict[str, Any], idempotency_store: IdempotencyStore) -> dict[str, Any]:
    execution_id = input_state["executionId"]

    def send_notification() -> dict[str, Any]:
        # A real deployment would publish to SNS/EventBridge here; the toy
        # domain just records that notification happened.
        return {"notified": True}

    result = run_idempotently(idempotency_store, _step_key(execution_id, "notify"), send_notification)
    return {**input_state, **result}


def _tables():  # pragma: no cover -- thin AWS wiring
    orders_table = boto3.resource("dynamodb").Table(os.environ["ORDERS_TABLE_NAME"])
    idempotency_table = boto3.resource("dynamodb").Table(os.environ["IDEMPOTENCY_TABLE_NAME"])
    return orders_table, IdempotencyStore(idempotency_table)


def validate_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # pragma: no cover
    orders_table, store = _tables()
    return validate(event, orders_table, store)


def process_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # pragma: no cover
    # RetryLaterError / NeedsDecisionError propagate uncaught here on
    # purpose -- Step Functions' own retry/catch policy on this state is
    # what handles them, per the blueprint's structure.
    orders_table, store = _tables()
    return process(event, orders_table, store)


def notify_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # pragma: no cover
    _, store = _tables()
    return notify(event, store)
