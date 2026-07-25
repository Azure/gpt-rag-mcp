# MCP contracts and safety

## Contract surface

An MCP capability contract includes:

- capability name and description;
- argument names, types, defaults, validation, and required status;
- result type, shape, ordering, limits, and serialization;
- prompt parameters and generated instruction semantics;
- resource URI and content semantics;
- mount, transport, session, and error behavior relied on by clients.

Changing any of these can affect orchestration even when Python call sites
still compile. Prefer additive compatible changes and coordinate breaking
changes with the orchestrator and `Azure/GPT-RAG`.

## Tool safety

- Treat all arguments and upstream content as untrusted data.
- Reject invalid identifiers, schemes, hosts, paths, sizes, and counts before
  provider access.
- Do not construct shell commands, queries, or filesystem paths from
  unvalidated input.
- Require explicit authorization for privileged or tenant-scoped data.
- Apply least privilege to credentials and provider operations.
- Bound network work with timeouts, response limits, and deliberate retries.
- Return useful, bounded results; do not expose raw provider payloads without
  a defined contract.
- Preserve causes in actionable errors without revealing secrets or sensitive
  content.

Descriptions and prompts help models choose capabilities; they are not
authorization, validation, isolation, or output-filtering controls.
