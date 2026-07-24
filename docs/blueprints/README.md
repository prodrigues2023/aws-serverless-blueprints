# The blueprint catalogue

Four serverless workload shapes. **Match the shape to the workload**, then honour the four serverless
truths every shape shares ([the ADRs](../adr)).

| Blueprint | Shape on AWS | Reach for it when | Its main failure mode |
| --- | --- | --- | --- |
| [Synchronous API](./synchronous-api.md) | API Gateway → Lambda → store | A client waits for the response | Cold-start latency in the request path |
| [Asynchronous fan-out](./async-fanout.md) | Event → queue/topic → Lambda | Work can happen after the response | Duplicate processing on redelivery |
| [Orchestrated workflow](./orchestrated-workflow.md) | Step Functions over Lambdas | A multi-step process needs state and retries | Orchestration where a queue would do |
| [Scheduled / batch](./scheduled-batch.md) | Schedule → Lambda over a dataset | Work runs on a clock | A run longer than the function timeout |

## How to read a blueprint page

Each page is the same five sections, so blueprints are comparable:

- **Intent** — the one-sentence job.
- **Structure** — the AWS services and how requests and events flow through them.
- **When to use / when not** — the honest boundary; the "when not" is the load-bearing half.
- **Failure modes** — how it goes wrong, as a property of the shape.
- **Serverless truths it must honour** — which of the four cross-cutting ADRs bite hardest here.

## The four truths, shared by all

No matter which blueprint you pick, these hold ([the ADRs](../adr)):

1. **Stateless and ephemeral** ([ADR-0002](../adr/0002-stateless-ephemeral.md)) — state lives in a
   managed store.
2. **At-least-once** ([ADR-0003](../adr/0003-at-least-once.md)) — idempotent handlers, dead-letter
   queues.
3. **Cold start and concurrency** ([ADR-0004](../adr/0004-cold-start-and-concurrency.md)) — the
   latency and cost model, designed around.
4. **Least privilege per function** ([ADR-0005](../adr/0005-least-privilege-per-function.md)) — one
   role each, minimum permissions.

The blueprint tells you the shape; the truths tell you what every shape must respect.
