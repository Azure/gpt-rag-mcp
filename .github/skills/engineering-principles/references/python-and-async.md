# Python and async implementation

- Python 3.12 and repository configuration take precedence over generic style
  preferences.
- Prefer explicit types, simple flow, intent-revealing names, and cohesive
  functions at one level of abstraction.
- Public capability helpers should document behavior, outputs, exceptions,
  side effects, and relevant limits rather than restating signatures.
- Keep framework, transport, and provider details at focused boundaries.
- Do not add abstractions without concrete variation or a boundary worth
  protecting.
- Remove duplicated knowledge rather than merely similar syntax.
- Preserve async correctness: synchronous provider, disk, process, or network
  calls must not block an async request path.
- Do not catch broad exceptions to return apparent success. Translate errors
  only where the caller can act, preserve the original cause, and avoid
  sensitive details.
- Keep mutable state scoped and concurrency-safe. Avoid request-dependent
  module globals.
- Use the formatter, linter, type checker, and tests configured by the
  repository. Do not introduce an overlapping tool without need.
