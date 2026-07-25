---
applyTo: "src/server.py,src/tools/**/*.py,src/resources/**/*.py,src/prompts/**/*.py"
---

# MCP runtime contracts and safety

- Runtime MCP capabilities are product code. They are distinct from GitHub
  Copilot engineering agents and skills under `.github/`.
- Treat capability names, descriptions, argument names and types, defaults,
  result shapes, resource URIs, prompt parameters, mounts, and error behavior
  as orchestrator-facing contracts.
- Prefer additive compatible evolution. Document and coordinate any rename,
  removal, required parameter, semantic change, or return-shape change with
  the GPT-RAG orchestrator and platform repository.
- Keep each tool focused and register it in `src/server.py`; do not inline
  unrelated provider or business logic into server wiring.
- Validate and bound untrusted inputs and outputs. Never interpolate arbitrary
  input into commands, paths, queries, URLs, or privileged Azure operations.
- Enforce authorization and least privilege in code or the provider boundary;
  descriptions and prompts are not controls.
- Bound external work with timeouts, response-size or item limits, and
  deliberate retry behavior.
- Avoid leaking secrets, credentials, personal data, or sensitive upstream
  responses through errors or tool results.
- Load `mcp-capability-development` for any capability or registration change.
- Exercise changed capabilities with the MCP Inspector and, when relevant,
  end to end through the orchestrator `mcp` strategy.
