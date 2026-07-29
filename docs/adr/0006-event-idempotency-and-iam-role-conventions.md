# ADR-0006: Event, idempotency, and IAM-role conventions

- **Status:** Accepted
- **Date:** 2026-07-28

## Context

[ADR-0002](./0002-stateless-ephemeral.md) through [ADR-0005](./0005-least-privilege-per-function.md)
establish four serverless truths every blueprint must respect, but not their shape: ADR-0003 says
every handler is idempotent, keyed on message identity — it does not say what that identity looks
like, where it is stored, or what happens on a race between two concurrent deliveries of the same
message. ADR-0005 says one least-privilege role per function — it does not say what "scoped to the
minimum" looks like as an actual policy statement a reviewer can check a pull request against.

Left unspecified, each blueprint (or each engineer implementing one) invents its own event
envelope, its own dedupe table shape, and its own idea of how tight "least privilege" actually is
in practice. [Milestone 3](../../ROADMAP.md#milestone-3--reference-deployments) needs these
specified once so "two blueprints could be built by different people and still share event,
idempotency, and role conventions" (the Milestone 2 exit criterion) is achievable at all.

Options considered:

1. **Leave it to each blueprint's implementation.** Cheapest to write, guarantees four
   incompatible dedupe-table shapes and four different ideas of "scoped enough," and makes a
   cross-blueprint resilience drill ([Milestone 4](../../ROADMAP.md#milestone-4--resilience-drills))
   impossible to run generically.
2. **Adopt a specific framework's conventions wholesale** (a particular IaC tool's idiomatic event
   shape, e.g.). Solves the shape problem by borrowing someone else's answer, but couples this
   catalogue to that framework's opinions in a repository whose whole premise is being buildable
   in any IaC tool.
3. **A minimal, tool-neutral convention for each of the three**, specified as field tables and
   policy shapes rather than a specific SDK's API.

## Decision

**Every blueprint's events, idempotency handling, and IAM roles follow one shared convention,
specified as data shapes and policy shapes rather than a particular IaC tool's syntax.**

- **Event envelope**: every event a blueprint's Lambda receives or emits carries a fixed set of
  envelope fields — `eventId`, `eventType`, `source`, `occurredAt`, `schemaVersion` — around a
  payload whose shape is free per `eventType`. `eventId` is what idempotency keys on.
  [docs/contracts/event-convention.md](../contracts/event-convention.md).
- **Idempotency**: a durable dedupe record, keyed on the event's identity, recorded before a
  handler's side effect and checked before every attempt — including the race where two
  deliveries of the same message are being processed concurrently, not just the easy case of a
  later, sequential redelivery. [docs/contracts/idempotency-convention.md](../contracts/idempotency-convention.md).
- **IAM roles**: one role per function, every statement resource-scoped to an ARN (never a
  service-wide wildcard) and action-scoped to the specific actions used (never `service:*`), with
  a required, reviewable justification per statement.
  [docs/contracts/iam-role-convention.md](../contracts/iam-role-convention.md).
- **Dead-lettering** is specified separately in
  [docs/contracts/dead-letter-convention.md](../contracts/dead-letter-convention.md), backed
  directly by [ADR-0003](./0003-at-least-once.md) rather than this ADR, since the DLQ decision
  was already made there — this ADR's idempotency convention and that one's dead-letter
  convention are companions, not duplicates: idempotency handles a message succeeding twice,
  dead-lettering handles a message that never succeeds.

## Consequences

**Positive**

- Milestone 2's own exit criterion becomes checkable: two blueprints built independently against
  these three conventions produce compatible event envelopes, compatible dedupe tables, and
  policies a reviewer can check the same way every time.
- The event envelope's `eventId` is the one piece of plumbing every other convention depends on —
  specifying it once here means the idempotency convention, the dead-letter convention, and any
  future observability convention all cite the same field instead of each inventing its own
  identity notion.
- IAM roles specified as data (statement shape + required justification) rather than a specific
  tool's syntax means the convention transfers to whichever IaC tool Milestone 3 picks, and a
  reviewer checks a policy against this ADR's shape regardless of the tool that generated it.

**Negative**

- A fixed envelope is one more thing every producer must conform to, including producers outside
  this repository's control (a third-party webhook, another team's service) — those need an
  adapter step to wrap incoming events into the envelope, which is real integration work this ADR
  does not remove.
- The idempotency convention's dedupe table is a new piece of state every handler now depends on
  — a dependency and an extra store to provision, exactly as ADR-0003 already disclosed as a
  negative consequence; this ADR does not reduce that cost, only specifies its shape.
- "Every statement resource-scoped and action-scoped" is a discipline, not a mechanism this ADR
  enforces by itself — a reviewer who approves a wildcard anyway has defeated the convention on
  paper, and nothing here prevents that short of the review actually happening.
