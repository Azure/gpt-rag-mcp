# Agent application MCP

NL2SQL-only, stateless Streamable HTTP `/mcp` using the official Python MCP SDK.
Product setup, SQL onboarding and operations belong to the
[central component documentation in Azure/AI-Landing-Zones](https://github.com/Azure/AI-Landing-Zones).

Python 3.12, `APP_CONFIG_ENDPOINT` bootstrap and a configured managed identity are required.

```sh
uv sync --frozen
uv run --frozen python -m uvicorn server:app --app-dir src --port 8080 --no-access-log
```

Importer help: `PYTHONPATH=src uv run --frozen python -m tools.nl2sql.importer --help`.
This component only deploys to an existing Container App. Candidate version: **1.0.0** (unpublished).
