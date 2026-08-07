# bad-single-run

The runner executes the migration tool exactly once per case and
asserts only the post-first-run state: the second-run block was
removed, so the transcript records one run and the escaped state is
never reached through the implementation's own journal. The defining
defect class of this target — behavior that is correct on a fresh
directory and wrong on a migrated one — is masked wherever it can
only be observed through a state the first run itself produced. The
re-migrating inner variant's first run is flawless; only a second
run against the same journal exposes it.

Freshness: state-masking was burned on a different inner target in
the predecessor set; the migration-journal locus of this fresh inner
target is new by construction (Q-BURN verifies).

deviation: state-masking @ migration-journal locus (oracle runs once; escaped second-run state unreachable)
