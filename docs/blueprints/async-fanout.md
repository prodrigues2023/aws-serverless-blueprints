# Asynchronous fan-out

## Intent

Decouple accepting work from doing it: an event lands on a queue or topic, and one or more Lambdas
process it independently — after the response, in parallel, at their own pace.

## Structure

```
producer → EventBridge / SNS → SQS queue → Lambda → store
                                   ↓ (on repeated failure)
                             dead-letter queue
```

A producer emits an event; a queue (SQS) or topic (SNS/EventBridge) buffers it; consumer Lambdas pull
and process. The buffer absorbs bursts and decouples producer speed from consumer speed. Every consumer
is idempotent and every queue has a dead-letter queue for messages that fail repeatedly
([ADR-0003](../adr/0003-at-least-once.md)).

## When to use

- The work can happen *after* the request is acknowledged — accept it, return `202`, process
  asynchronously.
- Bursty load needs a buffer so a spike does not overwhelm the consumer or a downstream.
- Several independent things must happen from one event — fan out to parallel consumers.

## When not to use

- A client is waiting for the result — that is the [synchronous API](./synchronous-api.md) blueprint.
- The steps are dependent and stateful, needing coordination and per-step retry — reach for the
  [orchestrated workflow](./orchestrated-workflow.md) blueprint rather than chaining queues by hand.

## Failure modes

- **Duplicate processing on redelivery.** The queue delivers at least once, so without idempotency a
  redelivered message double-processes — the failure mode this blueprint owns
  ([ADR-0003](../adr/0003-at-least-once.md)).
- **Poison messages.** A message that always fails is retried forever, blocking or wasting the
  consumer, unless a dead-letter queue catches it after N attempts.
- **Silent backlog.** If consumers cannot keep up, the queue grows unboundedly and latency climbs
  invisibly — queue depth must be monitored, not assumed.
- **Ordering assumptions.** Standard queues do not guarantee order; logic that assumes it is subtly
  wrong.

## Serverless truths it must honour

- **At-least-once** ([ADR-0003](../adr/0003-at-least-once.md)) is the defining truth here — idempotent
  consumers and a dead-letter queue are non-negotiable, not optional hardening.
- **Stateless** ([ADR-0002](../adr/0002-stateless-ephemeral.md)) — consumers carry no state between
  messages; the store and the message do.
- **Concurrency** ([ADR-0004](../adr/0004-cold-start-and-concurrency.md)) — consumer concurrency is
  capped to protect a downstream that cannot scale as fast as Lambda can.
- **Least privilege** ([ADR-0005](../adr/0005-least-privilege-per-function.md)) — each consumer's role
  reaches only its queue, its dead-letter queue, and its store.

> This blueprint is the AWS-concrete application of the provider-neutral messaging patterns —
> transactional outbox, idempotent consumers, dead-lettering — in the
> [event-driven-dotnet-reference](https://github.com/prodrigues2023/event-driven-dotnet-reference), and
> it generalises the high-throughput design in
> [iot-realtime-ingestion](https://github.com/prodrigues2023/iot-realtime-ingestion).
