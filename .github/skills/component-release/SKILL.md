---
name: component-release
description: Prepares and validates GPT-RAG MCP component releases. Use for versions, dependency locks, changelog entries, release branches, tags, GitHub Releases, and platform pin coordination.
---

# GPT-RAG MCP component release

Read `.github/copilot-instructions.md` completely before changing a release
artifact.

1. Determine the semantic version and create `release/x.y.z` from current
   `main`.
2. Set `VERSION` and `project.version` in `pyproject.toml` to `X.Y.Z`.
3. Regenerate `uv.lock` from the exact committed project metadata and inspect
   dependency changes.
4. Add `## [vX.Y.Z] - YYYY-MM-DD` to `CHANGELOG.md` with accurate Keep a
   Changelog categories.
5. Validate the exact release commit with the narrowest existing checks,
   startup or Inspector behavior as applicable, and a container build when
   dependency or packaging risk requires it.
6. Confirm whether `Azure/GPT-RAG` must update its MCP component pin and link
   the coordinated change.
7. Target the release pull request to `main`.
8. Use exactly `vX.Y.Z` for the Git tag and GitHub Release title.
9. Review release notes for secrets, personal data, and private Azure
   validation environment or resource-group names.
10. Re-fetch the published release and verify title, tag, body formatting, and
    target commit.

Do not publish a tag, release, package, image, or production deployment
without explicit human approval. Report missing validation or incompatible
platform pins as blockers rather than filling gaps by assumption.
