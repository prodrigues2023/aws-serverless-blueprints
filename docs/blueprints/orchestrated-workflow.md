# Orchestrated workflow

## Intent

Run a multi-step process that has state, per-step retries, branching, and a need for visibility: a Step
Functions state machine coordinates several Lambdas, owning the flow so the functions do not have to.

## Structure

```
trigger → Step Functions state machine
             ├─ step A (Lambda)  → retry / catch
             ├─ choice → step B or C
             └─ step D (Lambda)  → done / failed
```

Step Functions holds the workflow state, the transitions, the retry and catch policies, and the
execution history. Each Lambda does one step and stays stateless; the *orchestrator* remembers where
the process is, not the functions ([ADR-0002](../adr/0002-stateless-ephemeral.md)).

## When to use

- A process has several dependent steps, with branching, per-step retry, or compensation on failure.
- You need visibility into where an execution is and why it failed — the state machine's history gives
  it for free.
- Coordinating the steps by hand (chained queues, a function calling functions) would reinvent
  orchestration badly.

## When not to use

- The steps are independent and need no coordination — that is the
  [asynchronous fan-out](./async-fanout.md) blueprint; orchestration is overhead it does not need.
- It is a single step — a state machine around one Lambda is pure ceremony; use the
  [synchronous API](./synchronous-api.md) or fan-out blueprint.
- The workflow is extremely high-volume and simple, where per-transition orchestration cost outweighs
  its benefit.

## Failure modes

- **Orchestration where a queue would do.** The most common misuse: a state machine for steps that were
  independent, paying coordination cost and complexity for nothing — the failure mode this blueprint
  owns.
- **Cost surprise at volume.** Step Functions bills per state transition, so a chatty machine over huge
  volume can cost more than expected — the trade for its visibility and reliability.
- **Long-running executions and limits.** Very long or very large workflows meet service limits that
  must be designed for, not discovered.

## Serverless truths it must honour

- **Stateless functions, stateful orchestrator** ([ADR-0002](../adr/0002-stateless-ephemeral.md)) — the
  whole point is that the state machine holds the state so the Lambdas need not; this is where that
  truth is most cleanly expressed.
- **At-least-once** ([ADR-0003](../adr/0003-at-least-once.md)) — a step can be retried by the machine,
  so each step's action is idempotent; compensation handles steps that cannot simply be retried.
- **Least privilege** ([ADR-0005](../adr/0005-least-privilege-per-function.md)) — each step's Lambda has
  its own role, and the state machine's role is scoped to invoking exactly those functions.
- **Cold start** ([ADR-0004](../adr/0004-cold-start-and-concurrency.md)) matters less per step (the
  workflow is usually not in a tight latency budget) but compounds across many steps.
