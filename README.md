# AWS Serverless Blueprints

> Serverless is an architecture with its own failure modes, not "just deploy a function." A catalogue
> of the recurring serverless workload shapes on AWS — each honest about statelessness, at-least-once
> delivery, cold starts, and least privilege. Documented first, implemented in the open.

[![Phase](https://img.shields.io/badge/phase-2%20contracts-blue)](./ROADMAP.md)
[![ADRs](https://img.shields.io/badge/ADRs-6-green)](./docs/adr)
[![Blueprints](https://img.shields.io/badge/blueprints-4-blueviolet)](./docs/blueprints)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](./LICENSE)

Serverless is sold as simplicity — no servers, just functions — and that framing is how teams walk
into its failure modes unprepared. A function is stateless and ephemeral, so state kept in it vanishes.
Event sources deliver at least once, so a handler that is not idempotent double-processes. Cold starts
and concurrency limits are the real latency and cost model, invisible until traffic finds them. And a
function with a broad role is a broad blast radius. None of this is exotic; all of it is standard, and
all of it is skipped by "just deploy a function."

This repository is a catalogue of the serverless workload shapes that actually recur — a synchronous
API, an asynchronous fan-out, an orchestrated workflow, a scheduled job — each described as a blueprint:
when to use it, how it is structured on AWS, and how it fails. The failure modes are not an appendix;
they are the point.

**Português:** [README.pt-BR.md](./README.pt-BR.md)

---

## What is here today

| Area | Status | Link |
| --- | --- | --- |
| Context & scope | Done | [docs/context.md](./docs/context.md) |
| Blueprint catalogue | 4 blueprints | [docs/blueprints](./docs/blueprints) |
| Well-Architected notes | Done | [docs/well-architected-notes.md](./docs/well-architected-notes.md) |
| Architecture diagrams | Done | [docs/diagrams](./docs/diagrams) |
| Architecture Decision Records | 6 published | [docs/adr](./docs/adr) |
| Contracts — event, idempotency, IAM-role, dead-letter conventions | Done | [docs/contracts](./docs/contracts) |
| Reference deployments | Planned — Phase 3 | [ROADMAP.md](./ROADMAP.md) |

## The idea

**Pick the blueprint for the workload shape, and inherit the serverless truths that every shape must
respect.** The blueprints differ; four cross-cutting facts, each an ADR, do not:

- **Functions are stateless and ephemeral** ([ADR-0002](./docs/adr/0002-stateless-ephemeral.md)). State
  lives in a managed store — DynamoDB, S3 — never in the function's memory or disk between invocations.
- **Delivery is at-least-once** ([ADR-0003](./docs/adr/0003-at-least-once.md)). Event sources retry, so
  every handler is idempotent and every async path has a dead-letter queue. Exactly-once is a property
  you build, not one you are given.
- **Cold start and concurrency are the cost/latency model**
  ([ADR-0004](./docs/adr/0004-cold-start-and-concurrency.md)). They are designed around — provisioned
  concurrency where latency matters, concurrency limits where a downstream must be protected — not
  discovered in an incident.
- **Every function has its own least-privilege role**
  ([ADR-0005](./docs/adr/0005-least-privilege-per-function.md)). One function, one role, the minimum
  permissions — so the blast radius of a compromised or buggy function is bounded by construction.

[docs/contracts](./docs/contracts) specifies the checkable shape behind "idempotent" and "least
privilege": the event envelope, the dedupe-record mechanics (including the concurrent-delivery
race), the IAM policy-statement shape, and the dead-letter convention
([ADR-0006](./docs/adr/0006-event-idempotency-and-iam-role-conventions.md)).

## The blueprints

| Blueprint | Shape | Reach for it when |
| --- | --- | --- |
| [Synchronous API](./docs/blueprints/synchronous-api.md) | API Gateway → Lambda → store | A client waits for a response |
| [Asynchronous fan-out](./docs/blueprints/async-fanout.md) | Event → queue/topic → Lambda | Work can happen after the response, or in parallel |
| [Orchestrated workflow](./docs/blueprints/orchestrated-workflow.md) | Step Functions over Lambdas | A multi-step process needs state, retries, and visibility |
| [Scheduled / batch](./docs/blueprints/scheduled-batch.md) | Schedule → Lambda over a dataset | Work runs on a clock, not a request |

Each blueprint page is the same five sections — intent, structure, when / when not, failure modes, the
serverless truths it must honour — so they are comparable, and so the honest "when not" is never
skipped.

## Why documented first

The serverless mistakes are architectural, and they are expensive to unwind after they are live: a
handler that assumed exactly-once and quietly double-charges, a function holding state that evaporates
under scale, a broad role no one dares tighten. Choosing the right blueprint and respecting the four
truths is a design decision, far cheaper to get right on paper than to retrofit onto a running system
that has already been shaped by the wrong assumption.

## Roadmap

Four phases, tracked as GitHub milestones. See [ROADMAP.md](./ROADMAP.md).

1. **Blueprints** — the four shapes, their failure modes, the diagrams, the ADRs — done
2. **Contracts** — the event, idempotency, IAM-role, and dead-letter conventions every blueprint shares — done
3. **Reference deployments** — each blueprint as infrastructure-as-code you can deploy
4. **Resilience drills** — force retries, cold starts, and throttling; show each blueprint holding

## Related

- [serverless-ai-cicd-templates](https://github.com/prodrigues2023/serverless-ai-cicd-templates) — how these blueprints get deployed safely: OIDC, artifact promotion, least-privilege delivery
- [event-driven-dotnet-reference](https://github.com/prodrigues2023/event-driven-dotnet-reference) — the provider-neutral messaging patterns (outbox, idempotent consumers) the async blueprints apply
- [iot-realtime-ingestion](https://github.com/prodrigues2023/iot-realtime-ingestion) — a high-throughput ingestion design that the async fan-out blueprint generalises

## Author

Paulo Roberto Franco Rodrigues — AI Solutions Architect.
Recently designed enterprise AI frameworks and served on an AI architecture committee defining
the engineering standards that bring software discipline to AI delivery.
[LinkedIn](https://linkedin.com/in/paulo-roberto-franco-rodrigues)

## License

MIT — see [LICENSE](./LICENSE).
