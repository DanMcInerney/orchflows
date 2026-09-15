# Library context

Require Orchflows core `orchflows` 0.7.0+ with `orch-work`, `orch-review` and native child delegation. Resolve core through native skills, supplied package roots or core's `resolve` CLI. Core `docs/architecture.md` owns host controls and isolation.

The host must provide filesystem access to the caller's protocol workspace and enough fresh contexts for the declared roles. Python 3.11+ is required only for the bundled ledger validator. Report missing capabilities as a gap and stop when role separation or artifact identity cannot be established.

Keep protocols, versions, change maps, ledgers, reviews and returned probe evidence in the caller's workspace, never inside this library. This library contains no experiment harness, probe implementation or production runtime.
