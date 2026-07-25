---
applyTo: "VERSION,pyproject.toml,uv.lock,CHANGELOG.md"
---

# Component release surfaces

- Follow `.github/copilot-instructions.md` and load `component-release`.
- Use `release/x.y.z` for the branch and `vX.Y.Z` for the changelog heading,
  Git tag, and GitHub Release title.
- Keep `VERSION` and `project.version` in `pyproject.toml` equal to `X.Y.Z`.
- Regenerate `uv.lock` from the exact committed `pyproject.toml`; do not
  hand-edit dependency resolution.
- Keep Keep a Changelog categories and semantic-version impact aligned with
  observable behavior.
- Validate the exact release commit and identify the corresponding
  `Azure/GPT-RAG` component pin when coordinated platform work is required.
- Never infer versions from stale prose or a previous release.
- Never publish private Azure validation names, credentials, tokens, or
  personal data.
- A tag, GitHub Release, package, image, or deployment requires explicit human
  approval.
