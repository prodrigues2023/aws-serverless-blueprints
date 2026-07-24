# ADR-0004: Cold start and concurrency are the cost/latency model

- **Status:** Accepted
- **Date:** 2026-07-24

## Context

In a server-based system, latency and cost are shaped by machines you provisioned and can see. In
serverless, they are shaped by two things that are invisible until traffic finds them: cold starts and
concurrency. A cold start is the extra latency when the platform spins up a fresh execution environment
for an invocation that has no warm one waiting — the first request after idle, or the marginal request
when a burst outpaces warm capacity. Concurrency is how many invocations run at once, which the platform
scales automatically up to limits, and which determines both throughput and the load placed on
everything downstream.

Ignoring them produces two classic surprises. The latency surprise: a service is fast in testing and
occasionally, unpredictably slow in production, because those slow requests hit cold starts and nobody
modelled them. The cost-and-throttling surprise: a burst either fans out into so many concurrent
Lambdas that it overwhelms a database that cannot scale as fast, or hits a concurrency limit and throttles
— and either way the behaviour under load was never designed, only discovered.

These are not incidental; they are *the* performance and cost model of the platform. A serverless design
that does not address them has not been finished.

## Decision

**Cold start and concurrency are treated as the latency and cost model and designed around explicitly:
cold-start mitigation is applied where latency is user-facing, and concurrency is bounded where a
downstream must be protected.**

- **Cold-start mitigation is applied by blueprint, not blanket.** Where a client waits — the
  [synchronous API](../blueprints/synchronous-api.md) — provisioned concurrency or keeping functions
  warm can be worth its cost; where nobody waits — a [scheduled batch](../blueprints/scheduled-batch.md)
  — it usually is not. The same truth yields opposite decisions per shape.
- **Concurrency is bounded to protect downstreams.** A function fronting a database or a rate-limited
  API has a reserved/maximum concurrency set so a burst cannot fan out past what the downstream can
  take — the platform's willingness to scale is throttled deliberately.
- **The cost model is made visible per workload**, attributed rather than discovered on the bill — the
  same discipline the [llm-cost-observability](https://github.com/prodrigues2023/llm-cost-observability)
  repository applies to model cost, applied to invocation and duration cost.
- **Cold-start and concurrency behaviour is measured**, not assumed — cold-versus-warm latency and
  concurrency headroom are drilled ([Milestone 4](../../ROADMAP.md)) so the model is known before load
  finds it.

## Consequences

**Positive**

- Latency becomes predictable: the requests that would have been mysteriously slow are the ones
  cold-start mitigation was deliberately applied to, so the tail is designed rather than suffered.
- Downstreams are protected: bounded concurrency means a serverless burst cannot take out a database
  that scales more slowly, turning Lambda's elasticity from a hazard into a controlled input.
- Cost is understood per workload up front, so the invocation-and-duration bill holds no surprises.

**Negative**

- Cold-start mitigation costs money continuously (provisioned concurrency is paid whether used or not),
  so it is a real latency-versus-cost trade that must be made per blueprint, not a free win.
- Bounding concurrency to protect a downstream caps throughput, so the elasticity that made serverless
  attractive is deliberately limited — a correct but sometimes counterintuitive constraint.
- The cost and latency model depends on real traffic shapes; a design tuned for expected load can still
  be surprised by a genuinely novel burst pattern, so the model is a well-informed estimate, not a
  guarantee.
