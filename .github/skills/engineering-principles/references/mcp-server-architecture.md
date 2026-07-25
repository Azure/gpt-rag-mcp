# GPT-RAG MCP server architecture

## Purpose and ownership

This repository owns one GPT-RAG runtime component: a Python 3.12 MCP server
implemented with FastMCP and Starlette. It exposes capabilities consumed by the
GPT-RAG orchestrator through the `mcp` strategy.

Preserve these boundaries:

- `src/server.py` composes the application, registers capabilities, manages
  lifespan, and exposes transport and health routes.
- `src/tools/` contains focused MCP tool implementations.
- `src/resources/` contains runtime MCP resources.
- `src/prompts/` contains runtime MCP prompt templates and helpers.
- `scripts/` and `azure.yaml` deploy the component.
- Infrastructure provisioning and the platform component manifest belong to
  `Azure/GPT-RAG`.
- `.github/agents/` and `.github/skills/` are engineering-time Copilot assets,
  not runtime MCP capabilities.

## Design questions

1. Is the behavior a runtime tool, resource, prompt, transport concern,
   deployment concern, or engineering procedure?
2. Which repository owns the behavior and compatibility decision?
3. What contract does the orchestrator observe?
4. Which identity, network, provider, and trust boundaries are crossed?
5. Can the logic be verified without a live provider?
6. What is the migration, rollback, or roll-forward path?

Prefer a focused capability module and thin registration over expanding
`src/server.py`. Prefer explicit typed contracts over implicit dictionaries or
duplicated knowledge of configuration keys.

## Sources of truth

- Read Python and dependency requirements from `pyproject.toml` and `uv.lock`.
- Read runtime registrations and transport behavior from `src/server.py`.
- Read component deployment behavior from `azure.yaml`, `Dockerfile`, and
  `scripts/`.
- Read umbrella infrastructure and component pins from `Azure/GPT-RAG`.
- Read service documentation from this repository and umbrella documentation
  from the `docs` branch of `Azure/GPT-RAG`.
