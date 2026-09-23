# Expected behavior

- **Real invocation, fresh workspaces.** The workflow and the baseline are invoked for real on fresh task workspaces, preserving instructions, tools and declared settings.
- **Evidence classes kept apart.** Delivered code is graded by outcome checks and regressions held outside the solver's workspace. Runner unit tests and prompt inspection remain harness evidence only.
- **Shortcuts closed.** Solver workspaces contain no future history or reference fixes. The adversary's attempts to edit tests, exit early or special-case checks are recorded and fail.
- **Fair verifiers.** Verifiers accept a valid alternative implementation and reject a plausible incomplete patch, deliberately broken copies of the reference, and the unchanged project. Interfaces the hidden checks call are stated publicly.
- **Measured difficulty.** Calibration repeats are measured against a declared difficulty target, and admitted tasks carry expert time estimates. Tasks the calibration system always solves are hardened, rejected or labeled anchors.
- **Honest delivery.** Patches, command output, scores, identities, the rejection log and cost and time limits are retained. Tasks changed after admission receive new identities.
