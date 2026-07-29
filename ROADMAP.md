# Roadmap

Four milestones. Each ships something usable on its own.

Track these as GitHub Milestones.

---

## Milestone 1 — Blueprints (docs only)

**Goal:** a reader can choose the right serverless shape and knows how it fails, before deploying
anything.

| Issue | Deliverable |
| --- | --- |
| Write context document | Problem, users, scope, explicit non-goals |
| Catalogue the four blueprints | Each: intent, structure, when / when not, failure modes |
| Well-Architected notes | How the blueprints map to the AWS pillars |
| Architecture diagrams | The four shapes and the at-least-once retry path |
| ADR-0001 | Record architecture decisions in ADRs |
| ADR-0002 | Functions are stateless and ephemeral |
| ADR-0003 | Delivery is at-least-once — idempotency and dead-lettering |
| ADR-0004 | Cold start and concurrency are the cost/latency model |
| ADR-0005 | Every function has its own least-privilege role |

**Exit criteria:** a reader can match a workload to a blueprint and name that blueprint's failure
modes, and every decision traces to a serverless truth every shape must respect.

---

## Milestone 2 — Contracts

**Goal:** the conventions every blueprint shares are specified once.

| Issue | Deliverable | Status |
| --- | --- | --- |
| Event convention | The shape of an event and its identity for idempotency | Done — [event-convention.md](./docs/contracts/event-convention.md) |
| Idempotency convention | How a handler dedupes a redelivered event | Done — [idempotency-convention.md](./docs/contracts/idempotency-convention.md) |
| IAM-role convention | One role per function, scoped to exactly what it touches | Done — [iam-role-convention.md](./docs/contracts/iam-role-convention.md) |
| Dead-letter convention | Where failed messages go and how they are reprocessed | Done — [dead-letter-convention.md](./docs/contracts/dead-letter-convention.md) |

**Exit criteria met** — the four conventions compose rather than restating each other: the event
convention's `eventId` is the field the idempotency convention keys its dedupe record on; the
IAM-role convention's example role includes the statement for that same dedupe table; the
dead-letter convention's replay step explicitly re-enters the idempotency convention's check
rather than reprocessing blindly. A reviewer checks any Milestone 3 deployment's role, dedupe
table, and DLQ against these four documents field by field, the same test named in
[docs/contracts/README.md](./docs/contracts/README.md).

Backed by [ADR-0006](./docs/adr/0006-event-idempotency-and-iam-role-conventions.md) (event and
idempotency and IAM-role conventions) and [ADR-0003](./docs/adr/0003-at-least-once.md) (the
dead-letter convention specifically, since that decision was already made there — the new ADR
doesn't restate it, only the missing three).

---

## Milestone 3 — Reference deployments

**Goal:** `make deploy BLUEPRINT=x` stands up each blueprint as infrastructure-as-code.

| Issue | Deliverable | Status |
| --- | --- | --- |
| Synchronous API | API Gateway, Lambda, and a store, with a per-function role | Done — [infra/synchronous-api](./infra/synchronous-api) |
| Asynchronous fan-out | Event source, queue, Lambda, and a dead-letter queue | Done — [infra/async-fanout](./infra/async-fanout) |
| Orchestrated workflow | A Step Functions state machine over several Lambdas | Done — [infra/orchestrated-workflow](./infra/orchestrated-workflow) |
| Scheduled / batch | A schedule triggering a Lambda over a dataset | Done — [infra/scheduled-batch](./infra/scheduled-batch) |
| Local / low-cost path | Deployable to a sandbox account cheaply, tear-down included | Partial — see disclosure below |

**What's actually verified vs. what's disclosed as pending:**

- The four conventions from Milestone 2 are implemented as real, executable Python
  (`handlers/shared/idempotency.py`, `handlers/shared/event_envelope.py`) and exercised by 31
  tests running against `moto`-mocked DynamoDB and SQS — the conditional-write race, the TTL
  field, partial-batch-failure reporting, and the step-key idempotency scheme all run for real,
  not by inspection.
- The four blueprint root configs and the four shared Terraform modules
  (`iam_role`, `idempotency_table`, `dead_letter_queue`, `lambda_function`) all pass
  `terraform validate` — syntax and type-checked against the provider schema. The `iam_role`
  module's `variable` `validation` blocks mechanically enforce
  [iam-role-convention.md](./docs/contracts/iam-role-convention.md)'s shape (no `service:*`
  actions, no `*` resources, a required justification) at plan time, with no AWS account
  involved.
- **What is not yet done:** no `terraform plan`/`apply` has been run against a real AWS account
  — this environment has no AWS credentials. `make deploy BLUEPRINT=x` is written and its
  `terraform init`/`plan`/`apply` sequence is correct, but actually standing up a blueprint (and
  the "local/low-cost path, tear-down included" deliverable) is pending real credentials. CI
  (`.github/workflows/ci.yml`) runs the credential-free checks — `terraform fmt -check`,
  `terraform validate` per directory, the moto-backed test suite, lint, and type-check — on every
  push, but does not and cannot verify an actual deploy.

**Exit criteria:** a first-time reader deploys each blueprint from one command and sees a per-function
role, a dead-letter queue, and an idempotent handler in place. **Partially met** — the
infrastructure-as-code, its credential-free validation, and the handler logic's real behavior
are all done; the actual deploy-and-observe step awaits an AWS account.

---

## Milestone 4 — Resilience drills

**Goal:** prove the failure modes are handled, not just named.

| Issue | Deliverable |
| --- | --- |
| Redelivery drill | Force a duplicate event; assert the handler processes it once |
| Cold-start measurement | Measure cold versus warm latency; show the mitigation's effect |
| Throttle drill | Exceed a downstream limit; assert concurrency control protects it |
| Dead-letter drill | Fail a message repeatedly; assert it lands in the DLQ and can be replayed |
| Blast-radius check | Confirm a function's role cannot touch what it should not |

**Exit criteria:** redelivery, cold starts, throttling, and poison messages are each demonstrated to be
handled by the blueprint, with evidence rather than assertion.
