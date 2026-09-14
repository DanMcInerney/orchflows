# Library context

Require Orchflows core `orchflows` 0.7.0+ with `orch-work`, `orch-review` and native child delegation. Resolve core through native skills, supplied package roots or core's `resolve` CLI. Core `docs/architecture.md` owns guidance selection and `docs/hosts.md` owns isolation and host controls.

Resolve context once at the outer entrypoint, including a leaf invoked alone. Select `design-iteration` from this library and the caller's task domains, such as `code`, `writing` or `visual-design`. Include `design-loop` if absent from the selected libraries, preserving the supplied library order. Resolve absolute primitive and guidance paths and pass them with the request context unchanged through composed workflows. Makers apply Make; reviewers apply Review. Extend context only for new dependencies, and preserve scoped caller model and effort choices without adding defaults.

The host must provide the tools needed to inspect, implement and test the requested project, preserve reproducible states, and research decision-relevant uncertainties. No fixed project runtime or research service is bundled. Report unavailable dependencies and blocked stages as gaps. Keep outputs, snapshots and evidence in the caller's workspace, never inside this library.
