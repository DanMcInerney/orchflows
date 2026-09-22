# Library context

Require core `orchflows` (`orchflows:orch-work`, `orchflows:orch-review`) and apply its `docs/architecture.md`.

Select collection guidance by scope: `research.search-site.web`, `.feeds`, `.lemmy` or another site specialization; use `research.search-site` for unfamiliar sites. Combine names for grouped scopes. Assessment selects `research.search-site` and `writing`. Preserve caller guidance/library order. Both leaves pass the [evidence contract](evidence.md).

When useful, resolve optional `research-acquire:research-acquire` once; pass its path and suitable Python to relevant workers. It owns reader routes and invocation. Native public tools can collect other sites. Missing optional readers limit access only if no usable route remains; missing required primitives, delegation or explicit guidance block dependent work.
