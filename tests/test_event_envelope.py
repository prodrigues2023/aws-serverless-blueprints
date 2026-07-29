import conftest  # noqa: F401
import pytest
from shared.event_envelope import (
    InvalidEventError,
    idempotency_key_from_api_request,
    parse_event,
    scheduled_run_key,
)

VALID_RAW = {
    "eventId": "5e8b6e2a-6e33-4f9a-9c2e-2f6a1e9b6b3f",
    "eventType": "order.refund_requested",
    "source": "orders-api",
    "occurredAt": "2026-07-28T14:03:00Z",
    "schemaVersion": "1",
    "data": {"orderId": "ORD-7", "amount": 24.99},
}


def test_parses_a_valid_envelope():
    event = parse_event(VALID_RAW)
    assert event.event_id == VALID_RAW["eventId"]
    assert event.idempotency_key == event.event_id
    assert event.data["orderId"] == "ORD-7"


def test_rejects_missing_required_field():
    raw = {k: v for k, v in VALID_RAW.items() if k != "eventType"}
    with pytest.raises(InvalidEventError):
        parse_event(raw)


def test_rejects_non_uuid_event_id():
    raw = {**VALID_RAW, "eventId": "not-a-uuid"}
    with pytest.raises(InvalidEventError):
        parse_event(raw)


def test_rejects_non_object_data():
    raw = {**VALID_RAW, "data": "not-an-object"}
    with pytest.raises(InvalidEventError):
        parse_event(raw)


def test_correlation_id_is_optional():
    event = parse_event(VALID_RAW)
    assert event.correlation_id is None
    with_correlation = parse_event({**VALID_RAW, "correlationId": "9d3c6a1e-8b2f-4e7a-9b1e-3f6a2e9b6b3f"})
    assert with_correlation.correlation_id == "9d3c6a1e-8b2f-4e7a-9b1e-3f6a2e9b6b3f"


def test_idempotency_key_from_api_request_is_case_insensitive():
    assert idempotency_key_from_api_request({"Idempotency-Key": "abc123"}) == "abc123"
    assert idempotency_key_from_api_request({"idempotency-key": "abc123"}) == "abc123"
    assert idempotency_key_from_api_request({"Content-Type": "application/json"}) is None


def test_scheduled_run_key_uses_intended_fire_time_not_actual_invocation():
    key_a = scheduled_run_key("nightly-cleanup", "2026-07-28T00:00:00Z")
    key_b = scheduled_run_key("nightly-cleanup", "2026-07-28T00:00:00Z")
    assert key_a == key_b == "nightly-cleanup:2026-07-28T00:00:00Z"
