# Well-Architected notes

The blueprints are not invented in a vacuum; they are the recurring shapes that fall out of applying the
AWS Well-Architected pillars to serverless workloads. This document maps the catalogue's four
cross-cutting truths onto the pillars, so a reviewer familiar with the framework can see where each
blueprint's obligations come from.

## The four truths against the pillars

| Serverless truth (ADR) | Primary pillar | Why it lands there |
| --- | --- | --- |
| Stateless and ephemeral ([ADR-0002](./adr/0002-stateless-ephemeral.md)) | Reliability | State in a managed store survives a function's disappearance; state in the function does not |
| At-least-once delivery ([ADR-0003](./adr/0003-at-least-once.md)) | Reliability | Idempotency and dead-lettering are how a retrying platform stays correct instead of double-acting |
| Cold start and concurrency ([ADR-0004](./adr/0004-cold-start-and-concurrency.md)) | Performance Efficiency & Cost Optimization | The latency and the bill are both functions of how invocations scale |
| Least-privilege per function ([ADR-0005](./adr/0005-least-privilege-per-function.md)) | Security | One tight role per function bounds the blast radius of a compromise or a bug |

## Pillar by pillar

**Operational Excellence.** Every blueprint is deployable as infrastructure-as-code
([Milestone 3](../ROADMAP.md)) and observable — structured logs, metrics, and traces on each function.
The orchestrated-workflow blueprint leans hardest here: Step Functions gives a multi-step process
visible state and per-step history, which is operability you would otherwise hand-build.

**Security.** Least privilege per function ([ADR-0005](./adr/0005-least-privilege-per-function.md)) is
the load-bearing security decision — the blast radius of any one function is exactly its role. Secrets
come from a managed secret store, never the function's environment in plain text, and the delivery
identity that deploys these blueprints is itself least-privilege
([serverless-ai-cicd-templates](https://github.com/prodrigues2023/serverless-ai-cicd-templates)).

**Reliability.** The two reliability truths — statelessness and at-least-once — are why every async
blueprint carries an idempotent handler and a dead-letter queue
([ADR-0003](./adr/0003-at-least-once.md)). A serverless system is reliable not because functions do not
fail, but because the architecture assumes they will and stays correct anyway.

**Performance Efficiency.** Cold start and concurrency
([ADR-0004](./adr/0004-cold-start-and-concurrency.md)) are the performance model. The synchronous-API
blueprint, where a client is waiting, is where cold-start mitigation earns its cost; a scheduled batch,
where nobody is waiting, is where it usually is not worth paying for — the same truth, opposite
conclusions, decided by the blueprint.

**Cost Optimization.** Serverless bills per invocation and per unit of duration, so cost is driven by
call volume, function duration, and over-provisioned concurrency. Cold-start mitigations (provisioned
concurrency) trade cost for latency, which is a decision each blueprint makes differently — and cost is
made *visible* per workload the way the [llm-cost-observability](https://github.com/prodrigues2023/llm-cost-observability)
repository makes model cost visible: attributed, not discovered on the bill.

**Sustainability.** Scaling to zero when idle is serverless's native sustainability advantage; the
scheduled-batch and async blueprints exploit it directly, doing work only when there is work.

## The point of the mapping

The blueprints are a way to *inherit* the Well-Architected guidance without re-deriving it each time. A
team that picks the right blueprint and honours its four truths has already satisfied the bulk of the
Reliability and Security pillars for that workload — which is the whole value of a blueprint over a
blank Lambda.
