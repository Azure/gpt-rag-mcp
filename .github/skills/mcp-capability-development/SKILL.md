---
name: mcp-capability-development
description: Designs and implements safe GPT-RAG MCP tools, resources, prompts, and registrations. Use whenever a runtime MCP capability or its orchestrator-facing contract changes.
---

# MCP capability development

1. Classify the capability as a tool, resource, prompt, or transport concern
   and confirm `Azure/gpt-rag-mcp` owns it.
2. Identify the orchestrator outcome, trust boundary, authorization model,
   external effects, limits, and compatibility constraints.
3. Define a narrow typed contract: name, description, arguments, defaults,
   validation, result shape, error behavior, and bounds.
4. Put focused logic in `src/tools/`, `src/resources/`, or `src/prompts/` and
   keep registration in `src/server.py` thin.
5. Treat all inputs and upstream content as untrusted. Validate schemes,
   hosts, identifiers, paths, sizes, and counts before effects.
6. Add timeouts, output limits, least-privilege access, and actionable
   non-sensitive errors at external boundaries.
7. Preserve compatibility or document and coordinate migration with the
   orchestrator and `Azure/GPT-RAG`.
8. Add focused behavior or contract tests when feasible.
9. Restore with `uv sync`, check import or startup behavior, exercise the
   capability with the MCP Inspector, and run orchestrator end to end when the
   integration contract changes.
10. Update this repository's documentation and the GPT-RAG docs branch when
    users or operators observe the change.

Never place this runtime capability under `.github/`; that directory contains
engineering-time Copilot assets only.
