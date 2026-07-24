# ADR-0003: Delivery is at-least-once — idempotency and dead-lettering

- **Status:** Accepted
- **Date:** 2026-07-24

## Context

The serverless event sources — SQS, SNS, EventBridge, and the async Lambda invocation path itself —
deliver at least once. A message can be delivered more than once because of a retry after a partial
failure, a visibility-timeout expiry, or the platform's own at-least-once guarantee. This is not a rare
edge; it is the contract. And it is invisible in normal operation, which is what makes it dangerous: the
handler works in testing, works in the demo, works most of the time in production, and then
double-processes under exactly the conditions — a retry, a timeout — that are hardest to reproduce.

The consequences are as severe as the platform's abstraction is smooth. A payment handler that is not
idempotent charges twice. An inventory decrement runs twice and oversells. An email sender sends
duplicates. The platform faithfully delivered the message again, as promised; the handler assumed it
would only ever see it once.

Separately, a message that *always* fails — a poison message — will be retried indefinitely against the
source's policy, wasting the consumer and potentially blocking a queue, unless there is somewhere for it
to go after N attempts.

## Decision

**Every handler is idempotent, and every asynchronous path has a dead-letter queue: processing the same
message twice has the same effect as processing it once, and a message that fails repeatedly is moved
aside for inspection rather than retried forever.**

- **Handlers are idempotent**, keyed on a message identity: the handler records that it processed a
  given message id (in the managed store, [ADR-0002](./0002-stateless-ephemeral.md)) and a redelivery
  of the same id is a no-op or a safe repeat, not a second effect.
- **Every async path has a dead-letter queue.** After a bounded number of failed attempts, a message
  goes to a DLQ, so a poison message stops wasting the consumer and becomes a visible, inspectable
  item.
- **Exactly-once is treated as something built, not given.** The platform provides at-least-once;
  effectively-once is achieved by idempotency on top of it. No design assumes the platform will not
  redeliver.
- **DLQs are monitored and replayable** — a message in a DLQ is an alert and a thing that can be
  reprocessed after the bug is fixed, not a silent grave.

## Consequences

**Positive**

- The system stays correct under the platform's real delivery guarantee: a redelivery, a retry, a
  timeout-driven duplicate all resolve to the intended single effect instead of a double charge or an
  oversell.
- Poison messages are contained: one bad message lands in a DLQ instead of blocking a queue or burning a
  consumer indefinitely.
- Building idempotency in makes retries *safe*, which in turn makes aggressive retrying a resilience
  tool rather than a hazard.

**Negative**

- Idempotency requires a durable dedupe record keyed on message identity, which is extra store writes,
  extra reads, and a retention policy for those keys — real cost and complexity for every handler.
- Choosing the idempotency key correctly is subtle; a key that is too coarse drops legitimately distinct
  messages, and one too fine fails to catch a true duplicate — either way the protection is silently
  wrong.
- Dead-letter queues are one more piece of infrastructure to provision, monitor, and operate, and a DLQ
  that nobody watches is just a place where failures accumulate unseen.
