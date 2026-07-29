"""The event convention (docs/contracts/event-convention.md), made
runnable: the envelope every event carries, and the two ways an
idempotency key is derived from it -- an event's own `eventId`, or an API
client's `Idempotency-Key` header for the synchronous-API case.
"""
import re
from dataclasses import dataclass
from typing import Any

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)

REQUIRED_FIELDS = ("eventId", "eventType", "source", "occurredAt", "schemaVersion", "data")


class InvalidEventError(ValueError):
    pass


@dataclass(frozen=True)
class Event:
    event_id: str
    event_type: str
    source: str
    occurred_at: str
    schema_version: str
    data: dict[str, Any]
    correlation_id: str | None = None

    @property
    def idempotency_key(self) -> str:
        """event-convention.md: `eventId` is what idempotency keys on."""
        return self.event_id


def parse_event(raw: dict[str, Any]) -> Event:
    """Validate and parse an envelope per event-convention.md. Raises
    InvalidEventError -- callers map this to the idempotency-convention.md
    NEEDS_DECISION-adjacent case of "reject before any side effect", not a
    retry-forever loop on a message that will never parse.
    """
    missing = [f for f in REQUIRED_FIELDS if f not in raw]
    if missing:
        raise InvalidEventError(f"event missing required field(s): {missing}")
    if not _UUID_RE.match(str(raw["eventId"])):
        raise InvalidEventError(f"eventId '{raw['eventId']}' is not a UUID")
    if not isinstance(raw["data"], dict):
        raise InvalidEventError("'data' must be an object")

    return Event(
        event_id=raw["eventId"],
        event_type=raw["eventType"],
        source=raw["source"],
        occurred_at=raw["occurredAt"],
        schema_version=str(raw["schemaVersion"]),
        data=raw["data"],
        correlation_id=raw.get("correlationId"),
    )


def idempotency_key_from_api_request(headers: dict[str, str]) -> str | None:
    """event-convention.md's API Gateway note: the client assigns the id
    via an Idempotency-Key header. None means the client opted out of
    idempotency protection for this call -- the handler must not
    fabricate a key on the client's behalf.
    """
    for name, value in headers.items():
        if name.lower() == "idempotency-key":
            return value
    return None


def scheduled_run_key(schedule_name: str, scheduled_fire_time: str) -> str:
    """idempotency-convention.md's "scheduled/batch: run identity" note:
    the key is the schedule name plus the *intended* fire time, not the
    actual invocation time -- so a retry of a run and the original run
    share the same key.
    """
    return f"{schedule_name}:{scheduled_fire_time}"
