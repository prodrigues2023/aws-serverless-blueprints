# IAM-role convention

Backs [ADR-0005](../adr/0005-least-privilege-per-function.md) and
[ADR-0006](../adr/0006-event-idempotency-and-iam-role-conventions.md). Specifies the shape of a
least-privilege role, so "scoped to the minimum permissions" is a policy statement a reviewer
checks field by field, not a judgement call made once and never revisited.

## Naming

`{service}-{function}-role`, e.g. `orders-refund-handler-role`. One role, one function, always —
never a role shared across two functions, even two functions that currently happen to need the
same permissions (ADR-0005: their needs will diverge, and a shared role means the divergence
either broadens both or is silently not applied to one).

## Statement shape

Every statement in every function's policy has all four fields; none are inferred or left
implicit:

| Field | Requirement | Notes |
| --- | --- | --- |
| `Effect` | `Allow` only | A `Deny` statement suggests the role's `Allow` set is already too broad and is being narrowed with a patch — fix the `Allow` set instead. |
| `Action` | Specific actions, never `service:*` | `dynamodb:GetItem`, not `dynamodb:*`. List every action the function actually calls; an action added to the code without a matching policy update fails at runtime, which is the intended failure mode (loud, at deploy or first invocation) rather than the alternative (silent, because a wildcard already covered it). |
| `Resource` | A specific ARN, never `*` and never a whole-service pattern | The exact table, the exact queue, the exact bucket-and-prefix this function touches — not "any table," not "any queue this account owns." |
| `Justification` | A one-line comment on the statement | *Why* this function needs this action on this resource. Required so a reviewer checks the claim against the function's actual code path, not just the policy's shape — a syntactically perfect least-privilege statement for the wrong reason is still a mistake waiting to be found later. |

## Read/write split

A function that only reads a resource never receives write actions on it, even if a future
feature might need them — that is a role change to make when the feature ships, reviewed
alongside the code that needs it, not a permission granted early "to save a step." Concretely for
the three stores this catalogue's blueprints use most:

| Resource | Read-only actions | Write actions |
| --- | --- | --- |
| DynamoDB table | `dynamodb:GetItem`, `dynamodb:Query` | `dynamodb:PutItem`, `dynamodb:UpdateItem`, `dynamodb:DeleteItem` |
| SQS queue | `sqs:ReceiveMessage`, `sqs:GetQueueAttributes` | `sqs:SendMessage`, `sqs:DeleteMessage` (a consumer needs both receive and delete — deleting is how it acknowledges, not a write to the business data) |
| S3 bucket/prefix | `s3:GetObject` | `s3:PutObject`, `s3:DeleteObject` |

## Example: an async-fan-out consumer's role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"],
      "Resource": "arn:aws:sqs:us-east-1:123456789012:order-refunds-queue",
      "Justification": "Consumes and acknowledges messages from its own queue only."
    },
    {
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"],
      "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/orders",
      "Justification": "Reads order state and writes the refund result (idempotency-convention.md's dedupe write is a separate table, separate statement below)."
    },
    {
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"],
      "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/idempotency-keys",
      "Justification": "Reads and writes its own dedupe records per idempotency-convention.md."
    }
  ]
}
```

Note there is no statement for the dead-letter queue's `SendMessage` — that action is granted to
the *queue's redrive policy*, an SQS-level configuration, not to the consuming function's role;
the function never sends to the DLQ itself. See the
[dead-letter convention](./dead-letter-convention.md).

## The role travels with the function

The policy document lives in the same infrastructure-as-code change as the function it belongs
to ([ADR-0005](../adr/0005-least-privilege-per-function.md)), reviewed in the same pull request —
never edited separately in the console. A permission added outside that review is exactly the
"broadened just this once" erosion ADR-0005 names as least privilege's main practical risk.

## Fields that do not apply

The Step Functions state machine in the [orchestrated workflow](../blueprints/orchestrated-workflow.md)
blueprint has its own role, following this same shape, scoped to `states:StartExecution` (or
`InvokeFunction` where the workflow calls Lambda directly) against exactly the ARNs of the
functions that workflow orchestrates — nothing here is specific to Lambda roles alone. Every
principal this catalogue creates (a function's role, a state machine's role, a scheduled rule's
invocation role) follows the same four-field statement shape.
