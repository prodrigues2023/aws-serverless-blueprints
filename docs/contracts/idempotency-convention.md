# Idempotency convention

Backs [ADR-0003](../adr/0003-at-least-once.md) and
[ADR-0006](../adr/0006-event-idempotency-and-iam-role-conventions.md). Specifies the dedupe
record every handler checks and writes, so "the handler is idempotent" is a mechanism with a
defined race-condition behaviour, not a claim that happens to hold in the easy case and quietly
fails in the hard one.

## The dedupe record

One DynamoDB item per idempotency key, in a table dedicated to this purpose (never reusing the
domain table — mixing dedupe records into business data conflates two different retention and
access patterns).

| Field | Type | Notes |
| --- | --- | --- |
| `idempotencyKey` | string (partition key) | The event's `eventId` ([event convention](./event-convention.md)), or the API client's `Idempotency-Key` header for the synchronous-API case. |
| `status` | enum: `in_progress` \| `completed` \| `failed` | See "The concurrent-delivery race" below — `in_progress` is what makes this convention correct under concurrency, not just under sequential retries. |
| `result` | object \| null | The handler's response, cached so a duplicate request returns the *original* answer rather than recomputing (and potentially getting a different answer from a since-changed world). Null while `in_progress`. |
| `expiresAt` | number (epoch seconds, DynamoDB TTL) | See "Retention window" below. |
| `createdAt` | string (ISO-8601) | When this key was first seen — for debugging and for the retention-window discussion, not itself load-bearing for correctness. |

## The handler sequence

1. **Conditional write, `status: in_progress`.** `PutItem` with a condition expression that the
   item does not already exist (`attribute_not_exists(idempotencyKey)`). If the condition fails,
   go to step 4 — someone else (a concurrent delivery) got there first.
2. **Do the work.** The handler's actual side effect — the refund, the inventory decrement, the
   email.
3. **Update to `status: completed`**, with `result` set to the outcome. This is the record a
   future duplicate reads.
4. **If the conditional write in step 1 failed**, read the existing item:
   - `status: completed` → return the cached `result` directly. The side effect already
     happened; this delivery is a safe no-op.
   - `status: in_progress` → **this is the concurrent-delivery race**: two deliveries of the same
     message are being processed at (approximately) the same time, neither has finished yet.
     Do not proceed with the side effect. Either retry the read after a short backoff (the other
     delivery will likely finish and flip to `completed` shortly), or fail this delivery back to
     the queue to be retried later — never proceed with the side effect a second time just
     because the first attempt has not confirmed completion yet.
   - `status: failed` → the previous attempt did not complete successfully. Whether to retry the
     side effect here is a per-handler decision (some failures are safe to retry immediately,
     some need the failed record to be inspected first) — this convention does not prescribe
     one, only that the choice is deliberate, not a silent fall-through.

**Step 1's conditional write is what makes this correct under concurrency.** A version of this
convention that only checks "does a completed record exist" before doing the work — without the
`in_progress` state and the conditional write — has a race: two concurrent deliveries can both
pass the check before either has written anything, and both proceed to the side effect. The
`in_progress` state closes that window.

## Retention window

`expiresAt` is provisional at **7 days** past `createdAt` — long enough to cover any
plausible redelivery window (SQS's maximum message retention is 14 days; EventBridge retries
are bounded much shorter), short enough that the dedupe table does not grow unbounded. This
number is a starting point, not a measured optimum — a specific blueprint with a longer
plausible redelivery window (a downstream that retries for weeks, say) should widen it, and
should say so explicitly in that blueprint's own documentation rather than silently overriding
the convention.

## Scheduled/batch: run identity instead of event identity

[Scheduled/batch](../blueprints/scheduled-batch.md) has no producer-assigned `eventId` (see the
[event convention](./event-convention.md)'s "fields that do not apply" note). Its idempotency
concern is **overlapping runs**, not redelivered messages, so the idempotency key is a
**run identity**: `{scheduleName}:{scheduledFireTime}` — the schedule's name plus the exact
timestamp EventBridge Scheduler intended to fire, not the actual invocation time (which would
differ between an on-time run and a retry of it, defeating the purpose). Two invocations
claiming the same scheduled fire time are the same logical run; the dedupe record's `status`
field means the same three things (`in_progress` / `completed` / `failed`) applied to the whole
run rather than to one message.

## Fields that do not apply

None at the record level — every handler that writes uses this shape. What varies is only the
idempotency key's *source*: an event's `eventId`, an API client's `Idempotency-Key` header (see
the [event convention](./event-convention.md)'s API Gateway note), or a scheduled run's identity
as above. A blueprint whose writes are naturally idempotent without a dedupe record (a `PutItem`
that is the same regardless of how many times it is sent, with no side effect beyond the write
itself) may skip the record — but must say so explicitly, per-handler, rather than silently
omitting it, since "naturally idempotent" is a claim worth writing down and reviewing, not an
assumption.
