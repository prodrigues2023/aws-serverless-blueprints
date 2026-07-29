# Contracts

Milestone 1 named the four serverless truths every blueprint respects — stateless functions
([ADR-0002](../adr/0002-stateless-ephemeral.md)), at-least-once delivery
([ADR-0003](../adr/0003-at-least-once.md)), cold start and concurrency
([ADR-0004](../adr/0004-cold-start-and-concurrency.md)), and least privilege
([ADR-0005](../adr/0005-least-privilege-per-function.md)) — without specifying their shape. This
directory specifies the shape: the event envelope, the idempotency mechanism, the IAM role shape,
and the dead-letter convention every blueprint shares, so that **two blueprints built by different
people still produce compatible events, compatible dedupe tables, and reviewable roles**
(Milestone 2's exit criterion, verbatim).

| Contract | Backs | What it specifies |
| --- | --- | --- |
| [Event convention](./event-convention.md) | [ADR-0006](../adr/0006-event-idempotency-and-iam-role-conventions.md) | The envelope every event carries, and the identity idempotency keys on |
| [Idempotency convention](./idempotency-convention.md) | [ADR-0003](../adr/0003-at-least-once.md), [ADR-0006](../adr/0006-event-idempotency-and-iam-role-conventions.md) | How a handler dedupes a redelivered event, including the concurrent-delivery race |
| [IAM-role convention](./iam-role-convention.md) | [ADR-0005](../adr/0005-least-privilege-per-function.md), [ADR-0006](../adr/0006-event-idempotency-and-iam-role-conventions.md) | The shape of a least-privilege role a reviewer can actually check |
| [Dead-letter convention](./dead-letter-convention.md) | [ADR-0003](../adr/0003-at-least-once.md) | Where a message that never succeeds goes, and how it comes back |

## Tool-neutral, on purpose

These are field tables and policy shapes, not a specific infrastructure-as-code tool's syntax.
[Milestone 3](../../ROADMAP.md#milestone-3--reference-deployments) picks one tool concretely to
deploy each blueprint; these conventions are what that deployment has to satisfy, in whichever
tool implements it. A CloudFormation template, a CDK stack, and a Terraform module can all be
checked against the same event-envelope field table and the same IAM-policy shape.

## How a blueprint uses these

Every blueprint page's "Serverless truths it must honour" section names which ADRs it inherits.
Read alongside the matching contract here for the concrete shape — [ADR-0003](../adr/0003-at-least-once.md)
says *why* [asynchronous fan-out](../blueprints/async-fanout.md) needs idempotent consumers; the
idempotency convention says what the dedupe record actually looks like.

Not every blueprint needs every contract at full strength:
[scheduled/batch](../blueprints/scheduled-batch.md) has no inbound event to envelope in the usual
sense (its trigger is a schedule, not a message) but still needs the idempotency convention for
overlapping runs — see each contract's own "fields that do not apply" note for what a given
blueprint legitimately skips.

## Validating a reference deployment against these

Milestone 3's exit criterion is that a first-time reader deploying any blueprint "sees a
per-function role, a dead-letter queue, and an idempotent handler in place." The check is
mechanical: **take the deployed role's policy document and check it against the IAM-role
convention's field table; take a redelivered test event and check the handler processes it once;
take a message that fails N times and check it lands in the DLQ this convention specifies.** A
role with a wildcard action, or a handler with no dedupe check, is the deployment failing its own
contract — not a style nitpick to fix in a later pass.
