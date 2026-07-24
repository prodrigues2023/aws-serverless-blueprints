# ADR-0002: Functions are stateless and ephemeral

- **Status:** Accepted
- **Date:** 2026-07-24

## Context

A serverless function feels like a long-running program: it has memory, it has a filesystem, and within
a single warm invocation you can put something in a variable and read it back. That resemblance is a
trap. The execution environment is ephemeral — it can be frozen, reused, or discarded at any time, and
under concurrency there are many of them at once, each isolated. Anything a function stashes in memory
or on local disk to use "next time" is unreliable: next time may be a fresh environment, or a different
one, or the value may simply be gone.

Teams discover this as a class of baffling bugs. A counter that increments correctly in testing
under-counts in production because it lives in a per-environment variable. A cache that "works" serves
stale or empty results depending on which warm environment a request lands in. A file written to `/tmp`
in one invocation is missing in the next. Every one traces to treating an ephemeral environment as
durable.

## Decision

**Functions are treated as stateless and ephemeral: all state that must survive an invocation lives in
a managed store, and nothing durable is kept in the function's memory or local disk.**

- **Durable state lives in a managed store** — DynamoDB, S3, or another service built to hold it — never
  in a function-level variable or `/tmp` beyond the scope of a single invocation.
- **Local memory and disk are scratch only**, valid within one invocation and assumed gone after.
  Caching in memory is permitted only as a best-effort optimisation that is always correct when empty.
- **The orchestrator holds workflow state**, not the functions — which is exactly why the
  [orchestrated-workflow](../blueprints/orchestrated-workflow.md) blueprint uses Step Functions to
  remember where a process is.
- **Session and request state** ride in the store or the request itself, so any environment can serve
  any request identically.

## Consequences

**Positive**

- Functions scale horizontally without correctness problems: because no environment holds unique state,
  any invocation is interchangeable, which is what lets the platform run thousands at once safely.
- A whole class of concurrency bugs — miscounts, stale caches, missing files — is eliminated by
  construction rather than debugged after the fact.
- Statelessness makes retries and at-least-once ([ADR-0003](./0003-at-least-once.md)) tractable, since a
  re-run starts from durable state, not from a lost in-memory context.

**Negative**

- Every piece of state is now a call to a managed store, which adds latency and cost that an in-memory
  value would not — statelessness is correct and it is not free.
- The store becomes a dependency and a potential bottleneck for state a monolith would have kept in
  memory, so it must be sized and access-patterned deliberately.
- The discipline is easy to violate accidentally — an innocent-looking module-level variable or `/tmp`
  write reintroduces hidden state — and the resulting bug is intermittent and hard to trace, so
  vigilance is an ongoing cost.
