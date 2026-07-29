# Architecture Decision Records

Decisions are numbered, immutable once accepted, and superseded rather than edited.
See [ADR-0001](./0001-record-architecture-decisions.md) for the process itself.

| ADR | Title | Status |
| --- | --- | --- |
| [0001](./0001-record-architecture-decisions.md) | Record architecture decisions in ADRs | Accepted |
| [0002](./0002-stateless-ephemeral.md) | Functions are stateless and ephemeral | Accepted |
| [0003](./0003-at-least-once.md) | Delivery is at-least-once — idempotency and dead-lettering | Accepted |
| [0004](./0004-cold-start-and-concurrency.md) | Cold start and concurrency are the cost/latency model | Accepted |
| [0005](./0005-least-privilege-per-function.md) | Every function has its own least-privilege role | Accepted |
| [0006](./0006-event-idempotency-and-iam-role-conventions.md) | Event, idempotency, and IAM-role conventions | Accepted |

## How the accepted decisions fit together

They are the four serverless truths every blueprint inherits, whichever shape you pick:

- **0002** — a function is stateless and can vanish between invocations, so durable state lives in a
  managed store, never in the function.
- **0003** — the platform delivers at least once, so correctness under retry is built with idempotent
  handlers and dead-letter queues, not assumed.
- **0004** — cold start and concurrency are the real latency and cost model, designed around
  deliberately rather than met in an incident.
- **0005** — one least-privilege role per function bounds the blast radius of any single function to
  exactly what it was permitted.

These are not blueprint-specific; they are the platform's nature. The blueprints
([the catalogue](../blueprints)) choose a *shape*; these ADRs state what every shape must respect. The
most commonly-violated in practice is **0003** — at-least-once — because the platform hides the retry
and the double-processing only shows up as a subtle data bug in production.

**0006** is the odd one out on purpose: it does not add a new serverless truth, it gives 0003 and
0005 a shared, checkable shape. "Idempotent" and "least privilege" only become things a reviewer
can verify once there is a fixed dedupe-record shape and a fixed policy-statement shape to check
them against — see [docs/contracts](../contracts) for the field-level specification of 0003
through 0006.

## Template

```markdown
# ADR-XXXX: Title

- **Status:** Proposed | Accepted | Superseded by ADR-YYYY
- **Date:** YYYY-MM-DD

## Context

The forces at play: the requirement, the constraints, the options considered and why each
was or was not viable.

## Decision

What was decided, in the active voice. What was deliberately deferred.

## Consequences

**Positive** — what this buys.

**Negative** — what it costs, and what you will have to live with. An ADR with no negative
consequences has not been thought through.
```

## Disagreeing with a decision

Open an issue titled `ADR-XXXX: <your objection>`. Experience from running a serverless workload in
production — especially a case where one of these truths bit you — is the most useful kind.
