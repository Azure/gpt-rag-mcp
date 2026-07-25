---
name: documentation-consistency
description: Keeps GPT-RAG MCP service and umbrella documentation aligned with shipped behavior. Use for capabilities, configuration keys, deployment steps, endpoints, defaults, operations, or breaking changes.
---

# GPT-RAG MCP documentation consistency

1. Identify the user, orchestrator, or operator behavior that changed.
2. Search this repository for the capability, configuration key, endpoint,
   parameter, and previous terminology.
3. Update service setup and Inspector guidance in `README.md` and operational
   diagnosis in `TROUBLESHOOTING.md`.
4. If umbrella GPT-RAG deployment, configuration, or user experience changes,
   search and update the `docs` branch of `Azure/GPT-RAG` in the same
   coordinated change.
5. Keep repository READMEs focused; link to published GPT-RAG documentation
   instead of duplicating broad product guidance.
6. Verify examples against executable defaults and current protocol contracts.
7. Report every documentation file, branch, or pull request in the
   implementation handoff.

A visible change is incomplete until documentation is updated or the search
demonstrates that no documentation is affected.
