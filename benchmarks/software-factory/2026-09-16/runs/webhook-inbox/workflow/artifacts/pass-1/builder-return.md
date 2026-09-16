# Pass 1 builder return

Candidate: `<BUNDLE_ROOT>/runs/webhook-inbox/workflow/project`
Baseline: `30d2cde4c11a1912b47ca5256f6dd2a19419371e`; branch remains `master`.
Candidate manifest identity SHA256: `4f73c55c524e6aba3e05b373baa45d58e8fe895a0aed2a5bbeaea9f85df8a2f7`.
Patch SHA256: `643f7d0d31bc93e9c5ad9191e343f48e625fc18c4d38aa5f49024823bf772c5c`.

`candidate-manifest.json` hashes every tracked/intent-to-add source file, including immutable contract/smoke fixtures, and records caller-note separately. Caller-note bytes match supplied SHA256. No commit or branch switch was made. New authored files have intent-to-add index entries to make them visible in the checked diff; contents remain unstaged.

Implemented strict raw-header and body validation, constant-time tenant HMAC/token comparisons, inclusive time/size boundaries, SQLite WAL/FULL atomic durable idempotency, exact raw bytes/IDs, tenant-filtered insertion ordering, bounded pages with arbitrarily large canonical cursor handling, generic JSON errors, loopback factory/CLI lifecycle and readiness. Valid JSON numeric representations are emitted from validated stored raw bytes so floats cannot introduce Infinity or precision loss. Added 20 behavior tests plus unchanged 2 public smoke tests; operating instructions and release preparation are in README.md and RELEASE_HANDOFF.md.

All required checks exit 0: public smoke, unittest discovery (22 tests), inbox.py compile, CLI help, git diff --check. `checks.json` records candidate identity and raw output path for each. `candidate.patch` contains tracked changes and new authored files, excluding caller-note. A separate temporary Git index was populated from the pristine baseline, and `git apply --cached --check candidate.patch` passed against that baseline. Actual empty patch-check output is retained in patch-check.txt; the exit status is recorded in checks.json. Source manifest remained identical throughout checks.

Implementation repair observation: the first development test run passed behavior assertions but nine temporary-directory cleanups failed on Windows because test helper sqlite connections used transaction context managers without explicitly closing them. Replaced those test-only contexts with contextlib.closing. Storage operations already used finally-close correctly. All subsequent discovered tests passed. This initial exploratory output was observed through the tool; final raw required-check evidence is saved in full.

No independent review was attempted by this builder and no child was spawned. Four fresh reviews remain owned by the coordinator. No check failures remain. Operating limitations requiring security/deployment judgment: standard-library HTTP server has no TLS, admission/rate cap or process supervisor; socket timeout limits idle wait, not trickled total duration; Python JSON nesting/resource limits produce 400 for excessive nesting; no automatic retention deletion; health is process responsiveness only. These are documented rather than represented as production-ready capabilities.

No live release or simulator mutation occurred. Human security approval is mandatory, and simulator deployment is separately prohibited by the supplied release policy. Proposed rollout uses backup/integrity checks, loopback canary, tenant isolation/retry/restart checks and measured status/latency/disk gates before any authorized exposure. Rollback preserves latest DB/WAL and prefers a previously approved compatible binary; pristine starter cannot ingest and is not a viable functional fallback. If no compatible approved binary exists, disable ingestion and repair forward, with sender retries. Restoring an older backup needs explicit data-loss/reconciliation approval.

Source is frozen at this return; remaining final RESULT.json/HANDOFF.md aggregation and review decisions belong to the coordinator.
