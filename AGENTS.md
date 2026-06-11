## Engineering Standards

### Clean Code and Modularity

All implementations in this repository should follow clean code best practices.
This is a Python 3.12 **MCP server** (SSE) managed by `uv`, exposing tools,
resources, and prompts to the orchestrator; keep each tool focused and the
server wiring thin, and avoid letting any single module become a catch-all for
unrelated behavior.

- Keep each module and file focused on a single, clear responsibility.
- Extract non-trivial logic into the right layer under `src/` instead of
  growing the server module:
  - `src/tools/` — one focused module per tool; register tools rather than
    inlining their logic in the server.
  - `src/resources/` — MCP resources.
  - `src/prompts/` — prompt templates (no hardcoded prompts in code paths).
- Prefer small, cohesive `async` functions and classes. Respect async
  correctness — do not block the event loop with synchronous I/O.
- Reuse existing tool helpers and connectors before adding new ones. Avoid
  duplication and speculative abstractions; extract only when code is
  genuinely repeated or a file is mixing concerns.
- Use clear, intent-revealing names so the code reads without excessive
  comments. Comment only non-obvious decisions.

### Adding a Tool

Add a new capability as a self-contained module under `src/tools/` and
register it with the server, rather than expanding an existing tool with
unrelated behavior. Keep each tool's input/output contract explicit and
documented so the orchestrator can consume it reliably.

### Configuration, Secrets, and Contracts

- Read runtime settings from **Azure App Configuration** (label `gpt-rag`) via
  the existing config provider; resolve secrets through **Key Vault**
  references. Never hardcode endpoints, deployment names, or feature flags in
  code.
- Prefer typed, explicit data contracts (type hints, dataclasses, or Pydantic
  models) for every tool's parameters and return shape.
- Surface errors clearly and consistently through the logging helpers. Do not
  swallow exceptions or add silent fallbacks that hide a broken tool or
  connector. Never use `print` for diagnostics — use the configured logger.

### Running and Verifying

```powershell
uv sync
uv run python -m src.server
npx @modelcontextprotocol/inspector   # exercise the MCP endpoint interactively
```

There is no maintained `tests/` suite here. Verify a tool change with the MCP
inspector, then end to end via the orchestrator (set `AGENT_STRATEGY=mcp` and
`MCP_SERVER_URL` in App Config and restart the orchestrator Container App).
