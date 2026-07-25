---
applyTo: "AGENTS.md,.github/copilot-instructions.md,.github/agents/**/*.md,.github/skills/**/*.md,.github/instructions/**/*.md,.github/scripts/validate-agentic-assets.py,.github/workflows/validate-agentic-assets.yml"
---

# Copilot engineering assets

- These assets govern repository engineering and do not define runtime MCP
  tools, resources, or prompts.
- Keep `AGENTS.md` stable and repository-wide; put procedures in skills and
  path-specific rules in scoped instructions.
- Use lowercase kebab-case names and valid YAML frontmatter for agents and
  skills. Keep descriptions specific enough for automatic selection.
- Keep agents focused on a role and skills focused on a reusable procedure.
- Do not copy product runtime prompts or tool implementations into `.github/`.
- Preserve local links and run
  `python .github/scripts/validate-agentic-assets.py` after every asset change.
