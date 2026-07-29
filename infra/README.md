# Infrastructure as code

Four Terraform root configs, one per blueprint, each backed by the same shared modules and the
same `handlers/` deployment package.

| Directory | Blueprint | Docs |
| --- | --- | --- |
| [synchronous-api](./synchronous-api) | API Gateway → Lambda → orders table | [docs/blueprints/synchronous-api.md](../docs/blueprints/synchronous-api.md) |
| [async-fanout](./async-fanout) | SQS → Lambda, partial-batch-failure reporting, DLQ | [docs/blueprints/async-fanout.md](../docs/blueprints/async-fanout.md) |
| [orchestrated-workflow](./orchestrated-workflow) | Step Functions over validate/process/notify Lambdas | [docs/blueprints/orchestrated-workflow.md](../docs/blueprints/orchestrated-workflow.md) |
| [scheduled-batch](./scheduled-batch) | EventBridge Scheduler → Lambda scanning the orders table | [docs/blueprints/scheduled-batch.md](../docs/blueprints/scheduled-batch.md) |

## Shared modules

[modules/](./modules) holds the pieces every blueprint reuses, each implementing one of the
[Milestone 2 contracts](../docs/contracts):

- `iam_role` — one role per function; its `variable` `validation` blocks mechanically reject
  `service:*` actions, `*` resources, and a missing justification, per
  [iam-role-convention.md](../docs/contracts/iam-role-convention.md).
- `idempotency_table` — the dedupe table shape from
  [idempotency-convention.md](../docs/contracts/idempotency-convention.md).
- `dead_letter_queue` — a queue plus its `{queue}-dlq`, redrive policy, and a zero-messages
  CloudWatch alarm, per [dead-letter-convention.md](../docs/contracts/dead-letter-convention.md).
- `lambda_function` — generic function wiring shared across all four blueprints.

All four root configs zip the same `handlers/` directory (`data.archive_file.handlers`) and differ
only in which Lambda entrypoint(s) they wire up and which AWS resources front them.

## Running this

```bash
make validate               # terraform fmt -check + validate, every dir, no AWS credentials needed
make plan BLUEPRINT=x        # terraform plan against a real AWS account
make deploy BLUEPRINT=x      # terraform apply
make destroy BLUEPRINT=x     # terraform destroy
```

`BLUEPRINT` is one of `synchronous-api`, `async-fanout`, `orchestrated-workflow`,
`scheduled-batch`.

## What's verified here vs. what requires a real AWS account

`terraform validate` checks syntax and types against the provider schema — it needs no
credentials and runs in CI on every push (`.github/workflows/ci.yml`), alongside the 31
`moto`-backed handler tests that exercise the actual DynamoDB/SQS semantics these modules assume
(conditional writes, TTL, partial-batch-failure reporting).

`terraform plan`/`apply`/`destroy` need real AWS credentials, which this environment and its CI do
not have. That step — actually standing up a blueprint and observing it — is disclosed as pending
in [ROADMAP.md](../ROADMAP.md#milestone-3--reference-deployments), not silently skipped.
