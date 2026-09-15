---
name: protocol-readiness-loop
description: Run a bounded experiment-protocol stress, adjudication, revision and conformance loop until owner freeze review or an explicit stop.
disable-model-invocation: true
---

# Protocol Readiness Loop

Take one experiment protocol from draft to a decision-ready state. The owner authorizes the bounded loop once. Never freeze the protocol or run the experiment.

Read the [readiness contract](references/readiness-contract.md), [ledger contract](references/ledger-contract.md) and [library context](../../references/library-context.md). Resolve `orch-work` and `orch-review` once and keep the request context unchanged through the run.

## Start and bounds

Require the protocol path, any project rules reviewers need, a positive round limit defaulting to 3, and a nonnegative conformance-repair limit defaulting to 2 per revision. Record the starting path, SHA-256 and status. Previous versions are immutable.

State that this loop may revise only the protocol and its change map. It may not build software, harnesses, mechanism probes, experiment infrastructure or production artifacts. The coordinator alone maintains the convergence ledger beside the protocol; role workers do not edit it.

A round is consumed when its fresh stress test starts. A full non-repair round uses four fresh children: stress and adjudication through `orch-review`, revision through `orch-work`, and conformance through `orch-review`. Each conformance repair attempt uses one fresh updater and one fresh verifier. With round bound `N` and repair limit `C`, the maximum is `N * (4 + 2C)` children; early stops use fewer. No role verifies its own work. If the required fresh contexts are unavailable, stop rather than simulate independence.

## Roles

- **Stress tester:** finds ways the experiment could give a misleading answer or fail in execution. It returns `READY` or `NOT_READY` with cited findings and proposed stable failure classes.
- **Adjudicator:** rules separately on findings and proposed remedies, assigns or confirms stable failure classes, completes the dependency-closure and mechanizability checks, and does not edit.
- **Updater:** makes only accepted changes. It writes the next immutable protocol version and its change map.
- **Conformance verifier:** checks every accepted change and mapped dependency location. It does not search for new design problems.

## Loop

For each round:

1. Give a fresh stress tester the current protocol and required ground truth, not the author's reasoning or earlier verdicts. Test whether the experiment can give a trustworthy answer and can actually run as written. Distinguish documented, procedural, mechanically checked and technically enforced controls.
2. Give a fresh adjudicator the protocol and cited findings. Use `ACCEPT`, `MODIFY`, `REJECT` or `OWNER_DECISION_REQUIRED`. For every accepted or modified finding, require the full dependency-closure map and stable failure-class record from the readiness contract.
3. Apply the stops before revising:
   - When exact executable semantics cannot be settled reliably by artifact-only review, stop with `BLOCKED` and reason `MECHANISM_PROBE_REQUIRED`. Return only a bounded probe brief and required frozen evidence; do not build or run the probe.
   - When the same evidenced failure class survives or reappears after two completed revisions, stop with `BLOCKED` and reason `RECURRENT_FAILURE_CLASS`. Route to strategic review, or to a separately authorized mechanism probe when the mechanizability gate also applies.
   - When a choice changes the question, claim, risk tolerance, scope, cost or required assurance, collect all such choices and stop `OWNER_DECISION_REQUIRED`.
4. If only technical in-scope corrections remain, give a fresh updater the accepted findings and maps. It creates the next protocol version without overwriting any prior version and records `finding -> decision -> failure class -> dependency closure -> affected locations -> changes`. It may edit only that protocol version and change map.
5. Give a fresh conformance verifier the prior version, new version, accepted findings and complete change map. Missing, contradictory, extra or unverifiable changes fail conformance.
6. On conformance failure, preserve the failed candidate and verifier result. Use a fresh updater for one bounded repair and a fresh verifier for the next check. Do not start another stress test until conformance passes. When the per-revision repair allowance is consumed without a pass, stop with `BLOCKED` and reason `CONFORMANCE_REPAIR_LIMIT_REACHED`.
7. After conformance passes, begin the next round with a fresh stress test of the revised protocol. A fresh `READY` result after the latest conformance pass stops `READY_FOR_OWNER_FREEZE`.

After every phase, append one ledger record. Before returning, run the bundled validator when Python is available; otherwise record the validator result as `UNKNOWN` and have a fresh verifier check the ledger contract. Never infer missing timing: write `UNKNOWN`.

## Stop and return

Stop with exactly one existing top-level status:

- `READY_FOR_OWNER_FREEZE`: a fresh stress test returned `READY` after the latest conformance pass;
- `OWNER_DECISION_REQUIRED`: the owner gate fired;
- `ROUND_LIMIT_REACHED`: the bound was consumed without readiness;
- `BLOCKED`: required evidence, roles or tools were unavailable, or a structured stop reason fired;
- `INVALID`: role separation, artifact identity or the recorded sequence cannot be established.

Return the current protocol path and SHA-256, rounds attempted, conformance repairs used per revision, concise history, unresolved items, stable blocker counts, terminal reason, next owner action and convergence-ledger path plus validation result. A recommendation is never authorization to freeze, build a probe or infrastructure, or execute the experiment.
