# Testing and evidence

Choose validation according to the changed boundary:

- Pure local logic: focused unit tests.
- Tool signatures and serialization: contract tests and MCP Inspector calls.
- Provider adapters: integration-style tests with mocked external boundaries.
- Application composition: import, startup, lifespan, health, and transport
  checks.
- PowerShell or POSIX scripts: syntax plus behavioral parity checks.
- Dependency changes: `uv` lock consistency, import or startup, and container
  build when risk requires it.
- Orchestrator integration: end-to-end validation using `AGENT_STRATEGY=mcp`
  and the configured `MCP_SERVER_URL`.
- Identity and authorization: negative tests proving unauthorized access is
  denied.

There is currently no maintained `tests/` suite. Do not invent coverage.
Introduce focused tests when new behavior can be protected economically.

For every change, capture:

1. Acceptance criterion and observable result.
2. Commands run and results.
3. Relevant configuration and component versions.
4. Contract, compatibility, migration, and rollback impact.
5. Validation that could not run and resulting risk.

A successful deployment alone is insufficient evidence for authorization,
data correctness, protocol compatibility, or upgrade behavior.
