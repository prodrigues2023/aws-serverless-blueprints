# Scheduled / batch

## Intent

Run work on a clock rather than a request: a schedule triggers a Lambda that processes a dataset — a
nightly job, a periodic cleanup, a recurring report.

## Structure

```
EventBridge Scheduler → Lambda → iterate a dataset → store / output
                          ↓ (work too large for one invocation)
                    fan out to async processing
```

A schedule (EventBridge Scheduler) invokes a Lambda on a cadence. The Lambda processes the dataset, and
when the dataset is larger than one invocation can handle within its timeout, it fans the work out to
the [asynchronous](./async-fanout.md) blueprint rather than trying to do it all in one call.

## When to use

- Work runs on a cadence, not in response to a request — nightly aggregation, periodic sync, scheduled
  cleanup.
- Nobody is waiting for the result, so cold-start latency is irrelevant and cost can be minimised.

## When not to use

- The dataset is too large to finish inside the function timeout in one pass — do not stretch a single
  Lambda; fan out ([async fan-out](./async-fanout.md)) so each item or chunk is its own invocation.
- The work is actually event-driven (it should run when something *happens*, not on a clock) — use the
  async blueprint triggered by that event.

## Failure modes

- **A run longer than the function timeout.** The dataset grows past what one invocation can process in
  its time limit, and the job silently starts failing partway — the failure mode this blueprint owns.
  The fix is to fan out, not to keep raising the timeout.
- **Overlapping runs.** A run that takes longer than the schedule interval can overlap the next one,
  double-processing unless guarded — which is why even scheduled work is idempotent
  ([ADR-0003](../adr/0003-at-least-once.md)).
- **Silent failure.** Nobody is watching a scheduled job in real time, so a failed run can go unnoticed
  until its output is missing downstream — alerting on run success is essential.
- **Partial-progress loss.** A run that fails halfway, with no checkpoint, redoes everything on retry —
  costly and, without idempotency, incorrect.

## Serverless truths it must honour

- **At-least-once and idempotency** ([ADR-0003](../adr/0003-at-least-once.md)) — overlapping runs and
  retries mean a scheduled job must be safe to run twice, the same discipline as an event consumer.
- **Stateless** ([ADR-0002](../adr/0002-stateless-ephemeral.md)) — progress and checkpoints live in a
  store, so a failed run can resume rather than restart blindly.
- **Concurrency** ([ADR-0004](../adr/0004-cold-start-and-concurrency.md)) — fanning out a large dataset
  respects downstream concurrency limits rather than launching thousands of invocations at once.
- **Least privilege** ([ADR-0005](../adr/0005-least-privilege-per-function.md)) — the job's role reaches
  only the dataset it reads and the output it writes; cold start
  ([ADR-0004](../adr/0004-cold-start-and-concurrency.md)) is a non-issue since nobody is waiting.
