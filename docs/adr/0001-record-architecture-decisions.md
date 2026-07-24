# ADR-0001: Record architecture decisions in ADRs

- **Status:** Accepted
- **Date:** 2026-07-24

## Context

The value of this catalogue is not the four workload shapes — those are well known — but the honest
account of how each fails and the platform truths every one must respect. Those truths are
counterintuitive precisely because serverless is marketed as simple: "functions are ephemeral", "the
platform retries", "cold starts are your latency model" all contradict the frictionless story a team
was told when they adopted it. Counterintuitive rules that are not written down get quietly violated by
someone who believed the marketing.

Recording the decisions with their reasoning is what turns "why is my handler idempotent, that's extra
work" into a documented answer about at-least-once delivery, rather than an argument had again in every
review.

## Decision

**Record every architecturally significant decision as a numbered ADR**, using the format in
[the index](./README.md): Context, Decision, Consequences — with the negative consequences stated as
plainly as the positive.

- An ADR is immutable once accepted; a changed decision is a new ADR that supersedes the old.
- The four serverless truths are ADRs because they are the rules most likely to be dismissed as
  unnecessary by someone who has not yet been bitten by the failure they prevent.

## Consequences

**Positive**

- A reader sees why each serverless truth exists — tied to a concrete failure mode — and can respect it
  by understanding rather than by rote.
- The record defends the truths against the "serverless is simple, why all this ceremony" pressure that
  the platform's own marketing creates.

**Negative**

- The discipline has a cost, and skipping an ADR for a "small" choice is how the record grows gaps.
- AWS services evolve (new concurrency controls, new orchestration features), so a recorded decision can
  age; superseding keeps it current, but only if someone does it.
