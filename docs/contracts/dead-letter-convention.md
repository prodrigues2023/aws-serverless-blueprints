# Dead-letter convention

Backs [ADR-0003](../adr/0003-at-least-once.md), which already decided that every asynchronous
path has a dead-letter queue and that a DLQ is "monitored and replayable... not a silent grave."
This document specifies what that means concretely: the retry count, the naming, the retention,
the required alarm, and the replay mechanism.

## Retry count before dead-lettering

**3 attempts**, provisional. A message is delivered, and if the consumer's Lambda returns an
error (or the visibility timeout expires without a delete) three times, SQS's redrive policy
moves it to the DLQ on the fourth failure. Three is a starting point balancing two failure
shapes: too low, and a transient blip (a downstream's brief unavailability) dead-letters a
message that a fourth attempt would have processed fine; too high, and a genuinely poison
message consumes visibility-timeout cycles for longer before anyone is alerted. A specific
blueprint with a downstream known to have longer transient outages should raise this and say so
explicitly, the same disclosure discipline as the
[idempotency convention](./idempotency-convention.md)'s retention window.

## Naming

`{queue-name}-dlq`, e.g. `order-refunds-queue-dlq`. The redrive policy on the source queue names
this DLQ as its `deadLetterTargetArn`; nothing sends to it directly (see the
[IAM-role convention](./iam-role-convention.md)'s note that a consumer's own role has no
`SendMessage` permission on the DLQ — the redrive is an SQS-level mechanism, not an action the
function's code takes).

## Retention

**14 days** — SQS's maximum message retention period, used in full for the DLQ specifically
(the source queue itself typically needs far less, since a healthy message is consumed within
minutes). A message in a DLQ is evidence of a bug or an outage that needs a human response; 14
days is the longest runway this catalogue can give that response before the evidence expires
unread.

## The DLQ depth alarm is not optional

**A CloudWatch alarm on `ApproximateNumberOfMessagesVisible > 0` for every DLQ, with no delay and
no batching window** — the threshold is one message, not some count meant to filter noise,
because a DLQ is defined by ADR-0003 as something nothing should be routinely landing in. A
blueprint that provisions a DLQ without this alarm has built exactly the "silent grave" ADR-0003
explicitly said a DLQ must not be — the queue exists, catches the poison message correctly, and
nobody finds out.

## Replay

A dead-lettered message is not gone; it is set aside for after the underlying bug is fixed. The
replay mechanism is deliberately manual-trigger, not automatic:

1. **Inspect** the DLQ's messages — the payload plus, where the consumer logs it, the last
   failure reason — to understand *why* they failed before doing anything else.
2. **Fix** the bug, the downstream, or the data the messages exposed.
3. **Replay explicitly** — move messages from the DLQ back to the source queue (SQS's own
   [DLQ redrive feature](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html),
   or an equivalent scripted move), a deliberate action a human takes after confirming the fix —
   never an automatic requeue on a timer, which would just re-fail the same messages against the
   same unfixed bug and burn through the retry count again.
4. **Replayed messages go through the same idempotency check** as any other delivery
   ([idempotency convention](./idempotency-convention.md)) — a message that partially succeeded
   before failing is not reprocessed from scratch; the dedupe record's `status` reflects whatever
   state that message's `eventId` was actually left in.

## Fields that do not apply

Every asynchronous path in this catalogue has a DLQ per ADR-0003 with no exception — this
convention has no "does not apply" case for a blueprint that uses a queue at all. The
[synchronous API](../blueprints/synchronous-api.md) blueprint's request/response path has no
queue and therefore no DLQ; a failed synchronous request is a failed HTTP response, handled by
the client's own retry logic, not by this convention.
