# bad-construct-commit (near-miss)

The harness still executes two runs and still asserts the escaped
state — but the second run is executed against a freshly constructed
state directory whose migrated data and complete journal were
committed by the harness itself during setup, not carried over from
the implementation's own first run. The journal state the second run
sees is harness side-channel state. Everything else is lawful: run-1
assertions are intact, the environment is pinned, the manifest is
schema-valid, and every inner pool variant still splits exactly as it
does under the reference package — which is what makes this the
near-miss. The masking is narrow: any second-run defect reachable
only through the journal bytes the implementation itself wrote on
run 1 (rather than the harness's idealized commit) can no longer be
observed, and the two-run transcript law (same state directory across
runs) is the only check that separates this package from a lawful
one.

deviation: side-channel-state @ commit-on-construct-only locus (run 2 state dir initialized by the harness, not by run 1)
