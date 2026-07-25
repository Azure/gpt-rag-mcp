---
name: architecture-decision
description: Conducts and records a verifiable GPT-RAG MCP architectural decision. Use when a choice alters protocol contracts, runtime boundaries, identity, data, deployment, or operation with meaningful reversal cost.
---

# GPT-RAG MCP architectural decision

1. Load the relevant `engineering-principles` references.
2. Define context, constraints, affected repositories, and up to five
   prioritized characteristics with measures.
3. Compare at least two viable alternatives and the option of not changing.
4. Evaluate MCP compatibility, tool safety, async behavior, identity,
   authorization, network isolation, cost, operation, migration, and
   reversibility.
5. Record the decision under `docs/adr/` using
   [the ADR template](references/adr-template.md).
6. Define fitness functions, adoption order, rollback or roll-forward, and a
   review trigger.

Do not turn a framework or Azure service preference into a requirement. When
evidence is missing, record a time-bounded investigation and decision
criterion instead of guessing.
