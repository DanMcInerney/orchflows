# Protocol Readiness Loop

`protocol-readiness-loop:protocol-readiness-loop` takes one experiment protocol from draft to a decision-ready stop. Fresh roles stress the current version, adjudicate findings, make accepted revisions and verify conformance. Prior versions stay immutable, and the workflow never freezes the protocol or runs the experiment.

The workflow closes three common sources of false convergence:

- every accepted finding is traced through its semantic dependency closure rather than patched only where it was first observed;
- executable semantics that artifact-only review cannot settle stop as `BLOCKED` with reason `MECHANISM_PROBE_REQUIRED` and require a separately authorized bounded probe;
- a stable failure class that survives two completed revisions, or a conformance sequence that consumes its repair allowance, stops ordinary prose repair.

The five original terminal statuses remain the complete top-level vocabulary. New stop conditions use structured `BLOCKED` reasons, preserving compatibility for consumers that parse only the status. Each run writes a JSON Lines convergence ledger; the bundled validator checks its required fields, timing arithmetic and terminal routing.

## Install and dependencies

From a complete Orchflows checkout, run `python scripts/orchflows.py setup --example protocol-readiness-loop` with Python 3.11+. Setup preserves an existing library. Register and install `protocol-readiness-loop` from the resulting home catalog using core `docs/hosts.md`. The workflow is manual-only on Codex and Claude Code.

Requires Orchflows 0.7.0+, native child delegation and filesystem access to the protocol workspace. The ledger validator uses only Python's standard library. The workflow does not provide or build an experiment harness, mechanism probe or production artifact.

[Trial requests](trials/request.md) and [acceptance criteria](trials/expected-behavior.md) define repeatable behavioral checks. Repository fixtures establish the ledger and routing contract; they do not prove a particular protocol ready.
