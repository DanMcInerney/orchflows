# Library context

Apply core `docs/architecture.md` execution rules before planning assignments.

Establish context once at the outer entrypoint, including either leaf invoked alone; composed calls reuse it. Locate core primitives through native skills, supplied package roots or the core's `resolve` CLI. `orchflows:docs/architecture.md` owns guidance selection; `orchflows:docs/home.md` owns CLI resolution. Pass resolved absolute paths, request context and output locations unchanged to composed skills and primitives.

Select collection guidance by scope: `research.search-site.web`, `.feeds`, `.lemmy`, or another supplied site specialization; unfamiliar sites use `research.search-site`. Combine applicable names for grouped scopes. Assessment selects `research.search-site` and `writing`. Include caller-selected guidance and libraries in their supplied order. Both leaves pass the [evidence contract](evidence.md).

Resolve optional `research-acquire:research-acquire` once when useful, passing its skill path and a suitable Python to the relevant workers. That skill owns reader routes, scripts and invocation. Native public tools also support collection, including sites outside the reader roster. Missing optional readers are access limitations only when no usable route remains; missing required primitives, delegation or explicit guidance block dependent work.

Use the caller's output location or a task directory in the caller's workspace, outside packages.
