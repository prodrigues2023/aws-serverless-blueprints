# Context and scope

## The problem

Serverless is marketed on what it removes: no servers to manage, no capacity to plan, just code that
runs when called. That is genuinely liberating and it is also a trap, because the things it removes are
visible and the things it introduces are not. A team ships a function, it works in the demo, and then
production reveals a set of failure modes that were there the whole time, unmentioned by the "just
deploy a function" framing.

The function held some state in memory between requests — a cache, a counter, an accumulating list —
and under concurrency that state is wrong, because each invocation may run in a fresh, isolated
environment and the old one can vanish at any time. The event source that triggers the function
delivers at least once, so a retry after a partial success double-processes, and a handler that assumed
exactly-once quietly charges a card twice. Traffic grows and latency spikes on cold starts, or a burst
throttles because concurrency hit a limit no one had configured. And the function's role was made broad
"to get it working", so a bug or a compromise can reach far more than the function ever needed.

Every one of these is standard serverless knowledge and every one is skipped by the simple framing.
They are not obscure; they are the default failure modes of the platform, and the difference between a
serverless system that scales gracefully and one that fails mysteriously is whether the architecture
was designed with them in mind.

This repository is a catalogue of the serverless workload shapes that recur — synchronous API,
asynchronous fan-out, orchestrated workflow, scheduled batch — each written as a blueprint that names
its failure modes and the platform truths it must respect, so the trap is visible before it is sprung.

## Users

| User | Need |
| --- | --- |
| Engineer building on AWS serverless | The right shape for a workload, and its failure modes named up front |
| Architect | A vocabulary of serverless patterns to reason about and review a design |
| Team adopting serverless | To meet statelessness, at-least-once, and cold starts on paper, not in an incident |
| Anyone told "just use Lambda" | The literacy to see what that framing leaves out |

## In scope

- The recurring serverless workload shapes, each as a blueprint with its failure modes
  ([docs/blueprints](./blueprints))
- The cross-cutting serverless truths every blueprint respects: statelessness
  ([ADR-0002](./adr/0002-stateless-ephemeral.md)), at-least-once delivery
  ([ADR-0003](./adr/0003-at-least-once.md)), cold start and concurrency
  ([ADR-0004](./adr/0004-cold-start-and-concurrency.md)), least privilege
  ([ADR-0005](./adr/0005-least-privilege-per-function.md))
- How the blueprints map to the AWS Well-Architected pillars
  ([well-architected-notes.md](./well-architected-notes.md))

## Explicitly out of scope

Deliberate exclusions:

- **The delivery pipeline.** How these blueprints are built, promoted, and deployed safely — OIDC,
  artifact promotion, least-privilege deploy identity — is the
  [serverless-ai-cicd-templates](https://github.com/prodrigues2023/serverless-ai-cicd-templates)'s
  subject. This repository is the runtime application architecture, not the pipeline that ships it.
- **Provider-neutral messaging theory.** The outbox, idempotent-consumer, and saga patterns in the
  abstract are the [event-driven-dotnet-reference](https://github.com/prodrigues2023/event-driven-dotnet-reference)'s
  subject; the async blueprints here *apply* them on concrete AWS services.
- **A serverless-versus-containers debate.** This assumes serverless has been chosen for a workload and
  shows how to shape it well; when *not* to use serverless at all is a broader decision it does not
  relitigate.
- **Every AWS service.** The catalogue uses the core serverless building blocks (Lambda, API Gateway,
  Step Functions, SQS, EventBridge, DynamoDB, S3) as the vocabulary for the four shapes, not an
  exhaustive service tour.
- **Cost tuning to the last dollar.** Cold start and concurrency are treated as the cost/latency *model*
  to design around ([ADR-0004](./adr/0004-cold-start-and-concurrency.md)), not a line-item optimisation
  exercise.

## Key constraints

1. **Functions are stateless and ephemeral.** State lives in a managed store, never in the function
   between invocations — see [ADR-0002](./adr/0002-stateless-ephemeral.md).
2. **Delivery is at-least-once.** Every handler is idempotent and every async path has a dead-letter
   queue — see [ADR-0003](./adr/0003-at-least-once.md).
3. **Cold start and concurrency are designed around.** They are the latency and cost model, addressed
   deliberately — see [ADR-0004](./adr/0004-cold-start-and-concurrency.md).
4. **One function, one least-privilege role.** Each function's permissions are the minimum it needs —
   see [ADR-0005](./adr/0005-least-privilege-per-function.md).
5. **The failure mode is part of the blueprint.** No shape is documented without the honest account of
   how it goes wrong.

## Related documents

- [Blueprint catalogue](./blueprints) — the four shapes and how to choose between them
- [Well-Architected notes](./well-architected-notes.md) — the blueprints against the AWS pillars
- [Diagrams](./diagrams) — the four shapes and the at-least-once retry path
- [ADRs](./adr) — the cross-cutting decisions every blueprint inherits
