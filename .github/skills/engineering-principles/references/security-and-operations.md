# Security and operations

- Prefer managed identity, Azure CLI login-based access for operator scripts,
  and least-privilege RBAC.
- Store secrets in Key Vault and expose them through references, never literal
  values in source, App Configuration plaintext, logs, prompts, results, or
  release notes.
- Use Azure App Configuration label `gpt-rag` for shared runtime and
  deployment settings when the platform contract defines them.
- Preserve tenant and authorization boundaries across the orchestrator and
  MCP capability. Never rely on model intent as an access-control decision.
- Treat remote MCP endpoints as attacker-reachable. Validate hosts, schemes,
  payloads, sizes, session behavior, and credentials.
- Keep network-isolated GPT-RAG deployments viable and document any need for a
  connected runner, private endpoint, or ACR Task.
- Define timeouts, retries, limits, failure behavior, health checks, and
  recovery paths at external boundaries.
- Keep PowerShell and POSIX deployment paths behaviorally equivalent.
- Infrastructure provisioning belongs to `Azure/GPT-RAG`; this repository
  deploys the component into that provisioned environment.

Security claims require evidence. Configuration, descriptions, and prompts
alone are not enforcement.
