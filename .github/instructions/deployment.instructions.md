---
applyTo: "scripts/**/*.ps1,scripts/**/*.sh,azure.yaml,Dockerfile"
---

# MCP deployment and operations

- Infrastructure provisioning belongs to `Azure/GPT-RAG`; preserve the guard
  that blocks `azd provision` and `azd up` here.
- Keep PowerShell and POSIX deployment behavior aligned, including required
  settings, image naming, tagging, build fallback, and failure behavior.
- Treat `APP_CONFIG_ENDPOINT`, label `gpt-rag`, and required App Configuration
  keys as operational contracts.
- Quote paths and external input safely. Never echo secrets or private Azure
  validation environment and resource-group names.
- Do not hide missing prerequisites or continue after failed login,
  configuration retrieval, build, push, or Container App update.
- Keep the container on Python 3.12, non-privileged port 8080, and the
  committed `uv` project contract unless an intentional migration is approved.
- Use a reproducible dependency lock and keep production-only installation
  behavior explicit.
- Load `documentation-consistency` when deployment or operator steps change.
- Production deployment and image publication require explicit human
  approval.
