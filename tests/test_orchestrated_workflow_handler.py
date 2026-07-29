import conftest  # noqa: F401
from orchestrated_workflow.handler import notify, process, validate
from shared import IdempotencyStore, seed_orders


def _seed(orders_table):
    seed_orders(orders_table, [{"orderId": "ORD-7", "amount": 24.99, "status": "delivered"}])


def test_happy_path_through_all_three_steps(orders_table, idempotency_table):
    _seed(orders_table)
    store = IdempotencyStore(idempotency_table)
    state = {"orderId": "ORD-7", "executionId": "exec-1"}

    state = validate(state, orders_table, store)
    assert state["eligible"] is True

    state = process(state, orders_table, store)
    assert state["refunded"] is True
    assert state["amountRefunded"] == 24.99

    state = notify(state, store)
    assert state["notified"] is True

    order = orders_table.get_item(Key={"orderId": "ORD-7"})["Item"]
    assert order["status"] == "refunded"


def test_already_refunded_order_is_not_eligible(orders_table, idempotency_table):
    seed_orders(orders_table, [{"orderId": "ORD-7", "amount": 24.99, "status": "refunded"}])
    store = IdempotencyStore(idempotency_table)
    state = {"orderId": "ORD-7", "executionId": "exec-2"}

    state = validate(state, orders_table, store)
    assert state["eligible"] is False

    state = process(state, orders_table, store)
    assert state["refunded"] is False  # process short-circuits on ineligibility rather than refunding anyway


def test_step_functions_retrying_a_step_processes_it_once(orders_table, idempotency_table):
    """orchestrated-workflow.md: "a step can be retried by the machine, so
    each step's action is idempotent." Simulates Step Functions retrying
    the process step after, say, a transient Lambda timeout where the
    step actually succeeded but the response was lost."""
    _seed(orders_table)
    store = IdempotencyStore(idempotency_table)
    state = validate({"orderId": "ORD-7", "executionId": "exec-3"}, orders_table, store)

    first = process(state, orders_table, store)
    second = process(state, orders_table, store)  # Step Functions retries the same step

    assert first["amountRefunded"] == second["amountRefunded"] == 24.99
    order = orders_table.get_item(Key={"orderId": "ORD-7"})["Item"]
    assert order["status"] == "refunded"  # transitioned once, not re-applied


def test_different_executions_have_independent_idempotency_keys(orders_table, idempotency_table):
    """Two different workflow executions over two different orders must
    not collide on the same idempotency key."""
    seed_orders(
        orders_table,
        [
            {"orderId": "ORD-7", "amount": 24.99, "status": "delivered"},
            {"orderId": "ORD-42", "amount": 34.50, "status": "delivered"},
        ],
    )
    store = IdempotencyStore(idempotency_table)

    state_a = validate({"orderId": "ORD-7", "executionId": "exec-a"}, orders_table, store)
    state_b = validate({"orderId": "ORD-42", "executionId": "exec-b"}, orders_table, store)
    result_a = process(state_a, orders_table, store)
    result_b = process(state_b, orders_table, store)

    assert result_a["amountRefunded"] == 24.99
    assert result_b["amountRefunded"] == 34.50
