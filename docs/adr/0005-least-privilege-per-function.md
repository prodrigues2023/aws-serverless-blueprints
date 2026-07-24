# ADR-0005: Every function has its own least-privilege role

- **Status:** Accepted
- **Date:** 2026-07-24

## Context

Serverless multiplies the number of independently-deployed compute units — a system that was one service
becomes a dozen functions. Each function is an identity that can be granted permissions, and how those
permissions are granted decides the blast radius of the whole system. The path of least resistance is a
shared, broad role: one role with generous permissions, attached to every function, because it "just
works" and nobody has to think about exactly what each function touches. It is also the worst possible
security posture, because now every function can do everything any function needed, and a bug or a
compromise in the least-important function has the reach of the most-privileged one.

The granular size of serverless is precisely what makes least privilege both more important and more
achievable here than in a monolith. More important, because there are many identities and a broad grant
multiplies across all of them. More achievable, because each function does one small thing, so the
minimum set of permissions it needs is small and knowable — a single function's true requirements are
easy to enumerate in a way a monolith's are not.

## Decision

**Each function has its own IAM role, scoped to the minimum permissions that function actually needs —
one function, one role, least privilege — never a shared or broad role.**

- **One role per function**, not a shared role across functions. The blast radius of any function is
  exactly its own role's permissions, and no function inherits reach it does not use.
- **Each role is scoped to the specific resources and actions** the function touches: this queue, this
  table's these actions, this bucket prefix — not a wildcard over a service.
- **Read and write are distinguished** in the grant: a function that only reads a table does not get
  write, so a bug cannot corrupt what it was only meant to consume.
- **The role travels with the function as code** (infrastructure-as-code, [Milestone 3](../../ROADMAP.md)),
  reviewed alongside it, so tightening or auditing a permission is a code change, not console
  archaeology.
- The identity that *deploys* these functions is itself least-privilege — the delivery side of the same
  principle, owned by the
  [serverless-ai-cicd-templates](https://github.com/prodrigues2023/serverless-ai-cicd-templates).

## Consequences

**Positive**

- The blast radius of a compromised or buggy function is bounded to exactly what that one function was
  permitted — the strongest containment serverless's granularity makes available.
- Least privilege is genuinely achievable here because each function's true needs are small and
  enumerable, so the tight role is not an unreasonable burden.
- Roles-as-code make permissions reviewable and auditable, so a grant that is too broad is visible in a
  pull request instead of hidden in the console.

**Negative**

- One role per function is more roles to define and maintain — real overhead that the shared-role
  shortcut avoids, and a temptation to broaden "just this once" that erodes the whole principle.
- Getting a role exactly minimal is iterative: too tight and the function fails at runtime on a missing
  permission (sometimes only on a rare code path), too loose and the containment leaks — tuning it is
  ongoing work.
- A large system has many roles to reason about collectively, and least privilege per function does not
  by itself prevent a *combination* of functions from having broad reach — it bounds each blast radius,
  not the system's total surface.
