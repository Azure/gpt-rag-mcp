---
applyTo: "src/**/*.py"
---

# Python MCP implementation

- Python 3.12 and `pyproject.toml` are authoritative.
- Prefer explicit types, intent-revealing names, small cohesive functions, and
  public docstrings that explain behavior and contract.
- Keep `src/server.py` focused on application composition and registration.
  Put capability logic in the appropriate `src/tools/`, `src/resources/`, or
  `src/prompts/` module.
- Reuse existing helpers before adding dependencies or abstractions.
- Preserve async correctness. Do not perform blocking network, disk, process,
  or provider I/O on an async request path.
- Preserve the original cause when translating exceptions and use configured
  logging for runtime diagnostics.
- Do not add broad catches, silent defaults, success-shaped fallbacks, or
  mutable global request state.
- Keep imports package-correct for both local `uv` execution and the container
  entry point.
- Restore with `uv sync`; run the narrowest available checks and an import or
  startup check for changed runtime modules.
