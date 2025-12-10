# Changelog

All notable changes to this project will be documented in this file.  
This format follows [Keep a Changelog](https://keepachangelog.com/) and adheres to [Semantic Versioning](https://semver.org/).

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
