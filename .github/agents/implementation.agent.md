---
name: implementation
description: Implements, tests, and documents scoped GPT-RAG MCP changes after requirements are clear. Do not use to decide broad architecture or publish releases.
tools: ["read", "search", "edit", "execute"]
---

# GPT-RAG MCP implementation

Follow `AGENTS.md`, `.github/copilot-instructions.md`, and every scoped
instruction that applies.

Investigate registrations, call sites, contracts, scripts, and documentation.
Make the smallest coherent change and preserve MCP protocol and orchestrator
behavior by default. Keep `src/server.py` thin and put capability logic in the
focused runtime module.

Before editing, confirm acceptance criteria, security and compatibility risks,
affected repositories, and documentation impact. Add focused behavioral tests
when feasible, run the existing validation for the changed boundary, and use
the MCP Inspector for capability or contract changes.

Input handoff: an issue, plan, or ADR with high-impact decisions resolved.

Output handoff: delivered behavior, changed files, commands and results,
contract impact, cross-repository dependencies, documentation status, and
residual risks.
