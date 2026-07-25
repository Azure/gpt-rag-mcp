---
name: engineering-principles
description: GPT-RAG MCP architecture and implementation principles. Use for design, review, meaningful refactoring, Azure integration, security, protocol, testing, or operational changes.
---

# GPT-RAG MCP engineering principles

Load only the references needed:

| When the task involves | Read |
| --- | --- |
| Repository purpose, ownership, or runtime boundaries | [MCP server architecture](references/mcp-server-architecture.md) |
| Tools, resources, prompts, schemas, or protocol compatibility | [MCP contracts and safety](references/mcp-contracts-and-safety.md) |
| Python design, async behavior, or maintainability | [Python and async](references/python-and-async.md) |
| Identity, secrets, deployment, networking, or operations | [Security and operations](references/security-and-operations.md) |
| Tests, validation, compatibility, or evidence | [Testing and evidence](references/testing-and-evidence.md) |

Use these principles as design questions rather than dogma. Task requirements,
the current implementation, executable configuration, and protocol contracts
remain the sources of truth.
