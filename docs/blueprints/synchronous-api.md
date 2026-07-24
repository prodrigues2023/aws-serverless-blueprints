# Synchronous API

## Intent

Serve a request where a client is waiting for the response: API Gateway routes to a Lambda, which does
the work and returns, reading and writing a managed store.

## Structure

```
client → API Gateway → Lambda → managed store (DynamoDB / S3)
                          ↓
                     response to client
```

API Gateway handles routing, auth, throttling, and request validation at the edge. The Lambda holds
the request logic and returns synchronously. All state is in the store
([ADR-0002](../adr/0002-stateless-ephemeral.md)); the function keeps nothing between requests.

## When to use

- A client needs an answer *now* — a read, a create-and-confirm, a query.
- The work fits comfortably inside the request timeout and the client's latency budget.

## When not to use

- The work is slow, or can happen after acknowledging the request — return `202 Accepted` and hand off
  to the [asynchronous fan-out](./async-fanout.md) blueprint instead of making the client wait.
- The work is a multi-step process with its own state and retries — that is the
  [orchestrated workflow](./orchestrated-workflow.md) blueprint.
- The function is holding state in memory to serve subsequent requests — that state is unreliable under
  concurrency ([ADR-0002](../adr/0002-stateless-ephemeral.md)).

## Failure modes

- **Cold-start latency in the request path.** Because a client is waiting, a cold start is felt
  directly as a slow response — the failure mode this blueprint owns
  ([ADR-0004](../adr/0004-cold-start-and-concurrency.md)).
- **Downstream throttling under a burst.** A traffic spike fans into concurrent Lambdas that can
  overwhelm the store or a downstream service if concurrency is not bounded.
- **Timeout mismatch.** The API Gateway integration timeout and the Lambda timeout must agree, or the
  client gets a gateway timeout while the function keeps running and billing.

## Serverless truths it must honour

- **Cold start and concurrency** ([ADR-0004](../adr/0004-cold-start-and-concurrency.md)) bite hardest
  here — this is the blueprint where provisioned concurrency most often earns its cost, because latency
  is user-facing.
- **Stateless** ([ADR-0002](../adr/0002-stateless-ephemeral.md)) — no session state in the function;
  the store holds it.
- **Least privilege** ([ADR-0005](../adr/0005-least-privilege-per-function.md)) — the function's role
  reaches only the specific store items and downstreams it needs.
- At-least-once is less central here (the client retries a failed request), but a write triggered
  synchronously should still be idempotent so a client retry does not duplicate it
  ([ADR-0003](../adr/0003-at-least-once.md)).
