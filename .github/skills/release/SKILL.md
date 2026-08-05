---
name: release
description: Prepare, version, validate, tag, document, or publish a GPT-RAG MCP release. Use for release preparation, SemVer decisions, release branches, version bumps, changelog updates, release notes, Git tags, GitHub releases, packages, container images, or deployments.
---

# Release GPT-RAG MCP

Use this workflow for every release. Preparation may be automated, but publication is always a separate, human-approved phase.

## Safety rules

- Never create, move, delete, or push a release tag; create or edit a GitHub release; publish a package or container image; or deploy anything without explicit human approval for that publication action.
- Treat approval to prepare a release, open or merge a pull request, or run validation as insufficient approval to publish.
- Never create or modify Azure resources while preparing a release.
- Never expose secrets or private Azure or Microsoft identifiers in release notes, command output, commits, tags, or release metadata.
- Do not depend on a central release manifest. This repository's release sources are Git tags, GitHub releases, `VERSION`, `pyproject.toml`, and `CHANGELOG.md`.
- Do not introduce a release custom agent. Use this skill directly.

## 1. Establish the release baseline

Start from a clean, current `develop` branch and fetch tags:

```bash
git fetch origin develop main --tags
git status --short
git tag --sort=-version:refname
gh release list --limit 100
```

Read the complete contents of:

- `VERSION`
- `pyproject.toml` (`project.version`)
- `CHANGELOG.md`

Determine the latest published version from both reachable `vX.Y.Z` Git tags and GitHub releases. Tags and releases are the publication record; version files describe the checked-out source. Normalize only for comparison by removing one leading `v`.

Stop and reconcile before continuing when:

- the highest SemVer tag and highest GitHub release differ;
- a release title or tag is not exactly `vX.Y.Z`;
- `VERSION` and `project.version` differ;
- the version files do not match the latest published version on `develop`; or
- a tag points to an unexpected commit or a release targets a different tag.

Do not guess which source is correct. Report each value and its source, inspect the relevant history, and obtain maintainer confirmation for the reconciliation.

## 2. Select the next SemVer

Choose `X.Y.Z` according to Semantic Versioning:

- increment **major** for incompatible public behavior;
- increment **minor** for backward-compatible functionality; or
- increment **patch** for backward-compatible fixes, documentation, dependency maintenance, or operational corrections.

Pre-release identifiers are allowed only when the maintainer explicitly requests them. Never silently reuse or skip a published version.

Summarize the proposed version and rationale before changing files.

## 3. Create the release branch

Create the release branch from the current remote `develop`, not from `main` or a local stale branch:

```bash
git switch --create release/X.Y.Z origin/develop
```

The branch name must be exactly `release/X.Y.Z`.

## 4. Prepare release metadata

Update all repository-local version surfaces in one change:

1. Set `VERSION` to exactly `X.Y.Z` with no `v` prefix.
2. Set `project.version` in `pyproject.toml` to exactly `X.Y.Z`.
3. Move the applicable entries under `## [Unreleased]` in `CHANGELOG.md` into `## [vX.Y.Z] - YYYY-MM-DD`.
4. Leave a single empty `## [Unreleased]` section at the top for future work.
5. Ensure changelog claims are supported by changes since the previous release.

The release tag and GitHub release title must both be exactly `vX.Y.Z`. Do not use `X.Y.Z`, `release-X.Y.Z`, or any other variation.

Draft release notes from the versioned changelog entry. Keep them concise and public:

- include user-visible additions, fixes, changes, known limitations, and public issue or pull-request links when useful;
- remove subscription IDs, tenant IDs, resource-group names, private resource or host names, internal service names, private repository names, customer names, incident IDs, employee aliases, credentials, tokens, and non-public URLs;
- replace environment-specific examples with neutral placeholders;
- do not disclose embargoed vulnerabilities or private operational details.

Search the draft for sensitive-looking identifiers and manually review it before publication.

## 5. Validate the release candidate

Discover and run the validation already defined by the repository at the release commit:

1. Inspect `pyproject.toml`, lock files, contribution instructions, test directories, and GitHub workflow files.
2. Run every existing Copilot asset validation that covers `.github/skills/**`.
3. Run the smallest existing unit, lint, type-check, and build commands that cover the changed release metadata and affected product code.
4. Do not add a new validator merely to make release preparation pass.

Always verify release consistency, even when no dedicated validator exists:

- `VERSION` equals `project.version`;
- the version is valid SemVer;
- the changelog has exactly one `Unreleased` heading and one `vX.Y.Z` heading;
- no published changelog heading is duplicated;
- the intended tag and title are exactly `vX.Y.Z`;
- the release-note draft contains no private identifiers;
- the working tree contains only intended release changes.

Record the exact commands and results in the pull-request description.

## 6. Open the release pull request

Commit the release preparation on `release/X.Y.Z`, push that branch, and open a pull request targeting `main`.

The pull request must include:

- the previous and proposed versions;
- the SemVer rationale;
- the release-note draft;
- version/changelog consistency confirmation;
- validation commands and results;
- any known limitations or publication dependencies; and
- a clear statement that no tag, GitHub release, package, image, or deployment has been published.

Do not target `develop` for the release pull request. Do not publish from an unmerged pull request.

## 7. Publication approval gate

After the release pull request is approved and merged to `main`:

1. Fetch `main` and verify the merge commit contains the exact approved version and changelog.
2. Re-run the release consistency checks against that commit.
3. Present the commit SHA, exact tag/title `vX.Y.Z`, sanitized notes, and every intended publication destination.
4. Ask for explicit human approval to publish.

Only after that approval may the approved commit be tagged and the approved destinations be published. Approval is scoped to the listed version, commit, notes, and destinations; any change requires renewed approval.

Prefer an annotated tag:

```bash
git tag -a vX.Y.Z <approved-main-commit> -m "vX.Y.Z"
git push origin vX.Y.Z
gh release create vX.Y.Z --title vX.Y.Z --notes-file <sanitized-notes-file>
```

Run package, image, or deployment publication only when each destination was explicitly included in the approval. Never infer deployment approval from tag or GitHub release approval.

## 8. Reconcile failures and roll back safely

- **Before publication:** correct the release branch or pull request, re-run validation, and obtain approval for material changes.
- **Tag pushed, release not created:** verify the tag points to the approved commit. Do not recreate, move, or delete it. Fix the release failure and request approval to resume.
- **GitHub release created, downstream publication failed:** preserve successful immutable artifacts, document the partial state, fix the failure, and request approval to resume only the missing destinations.
- **Wrong commit or version published:** stop all publication. Do not force-move or delete tags or overwrite artifacts. Report the exact state and follow a maintainer-approved reconciliation, normally a new patch release.
- **Deployment failure:** stop; do not make ad hoc Azure changes. Use the repository's established rollback procedure and require explicit approval before retrying or rolling back.

Finish by comparing the Git tag, GitHub release, version files, changelog, and any explicitly approved published artifacts. Report discrepancies rather than claiming success.
