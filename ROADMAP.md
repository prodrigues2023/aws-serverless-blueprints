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

| Issue | Deliverable |
| --- | --- |
| Event convention | The shape of an event and its identity for idempotency |
| Idempotency convention | How a handler dedupes a redelivered event |
| IAM-role convention | One role per function, scoped to exactly what it touches |
| Dead-letter convention | Where failed messages go and how they are reprocessed |

**Exit criteria:** two blueprints could be built by different people and still share event,
idempotency, and role conventions.

---

## Milestone 3 — Reference deployments

**Goal:** `make deploy BLUEPRINT=x` stands up each blueprint as infrastructure-as-code.

| Issue | Deliverable |
| --- | --- |
| Synchronous API | API Gateway, Lambda, and a store, with a per-function role |
| Asynchronous fan-out | Event source, queue, Lambda, and a dead-letter queue |
| Orchestrated workflow | A Step Functions state machine over several Lambdas |
| Scheduled / batch | A schedule triggering a Lambda over a dataset |
| Local / low-cost path | Deployable to a sandbox account cheaply, tear-down included |

**Exit criteria:** a first-time reader deploys each blueprint from one command and sees a per-function
role, a dead-letter queue, and an idempotent handler in place.

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
