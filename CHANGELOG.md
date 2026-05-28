# Changelog

## [v0.3.8] - 2026-05-27

### Changed
- **Dependency refresh:** Updated the MCP SDK requirement to 1.23.0 and refreshed `uv.lock` with `PyJWT` 2.12.0.

## [v0.3.7] - 2026-05-27

### Changed
- **Dependency refresh:** Updated transitive runtime dependencies in `uv.lock`, including `urllib3`, `pygments`, `cryptography`, `idna`, `python-dotenv`, `python-multipart`, and `requests`.

All notable changes to this project will be documented in this file.  
This format follows [Keep a Changelog](https://keepachangelog.com/) and adheres to [Semantic Versioning](https://semver.org/).

## [v0.3.6] - 2026-05-27
### Fixed
- **Bash deploy image platform:** Added `--platform linux/amd64` to `scripts/deploy.sh` Docker builds so Apple Silicon hosts produce Azure Container Apps-compatible images. Fixes [Azure/GPT-RAG#464](https://github.com/Azure/GPT-RAG/issues/464).

### Changed
- **MCP runtime wording:** Clarified the README that this service is a Python FastMCP/Starlette MCP server consumed through GPT-RAG's `mcp` strategy, avoiding legacy Semantic Kernel or AutoGen variant confusion. Closes [Azure/GPT-RAG#463](https://github.com/Azure/GPT-RAG/issues/463).

## [v0.3.5] - 2026-02-04
### Fixed
- Fixed Docker builds on ARM-based machines by explicitly setting the target platform to `linux/amd64`, preventing Azure Container Apps deployment failures.
### Changed
- Standardized on the container best practice of using a non-privileged port (`8080`) instead of a privileged port (`80`), reducing the risk of runtime/permission friction and improving stability of long-running ingestion workloads.

## [v0.3.4] - 2025-12-10
### Changed
- Major updated simplifying gpt-rag MCP

## [v0.2.3] - 2025-08-31
### Changed
- Removed certain default tool configurations that were resulting in excessively long docker builds
- Added .dockerignore

## [v0.2.2] - 2025-08-31
### Changed
- Standardized resource group variable as `AZURE_RESOURCE_GROUP`. [#365](https://github.com/Azure/GPT-RAG/issues/365)

## [v0.2.1] - 2025-08-08
### Changed
- Updated azure.yaml to support azd deploy targeting the container app.
- Added bash scripts execution mode.

## [v0.2.0] - 2025-07-15
### Changed
- Updated to align with GPT RAG infrastructure v2.0.0.

## [v0.1.0] - 2025-07-15
### Changed
- Fixed hardcoded variables in configuration.
- Updated README documentation.
- Added documentation for MCP usage.
- Updated tooling with latest changes.
- Fixed max token handling.
- Added new messaging tools.

## [0.0.1] - 2025-05-20
### Added
- The first version of the GPT RAG MCP was created.
- Added support for Stdio, FastAPI, and SSE.
- Included initial set of tools.
