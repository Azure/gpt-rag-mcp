---
applyTo: "README.md,TROUBLESHOOTING.md,CONTRIBUTING.md,SECURITY.md,SUPPORT.md"
---

# Repository documentation

- Describe the current FastMCP and Starlette service and the orchestrator
  `mcp` strategy; do not restore legacy runtime terminology.
- Keep service setup, deployment, and Inspector guidance in `README.md` and
  operational diagnosis in `TROUBLESHOOTING.md`.
- Keep contribution, security, support, and conduct policy in their dedicated
  files rather than duplicating it.
- Verify commands, paths, endpoints, configuration keys, labels, and defaults
  against executable repository sources.
- Link to the published GPT-RAG documentation instead of copying broad product
  guidance into this component repository.
- Coordinate changes on the `docs` branch of `Azure/GPT-RAG` when this
  component changes umbrella deployment, configuration, or user experience.
- Never put secrets, personal data, or private Azure validation environment
  and resource-group names in examples.
- Follow `SECURITY.md`; do not direct vulnerability reports to public issues.
