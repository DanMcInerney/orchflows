# bad-vacuous (inert)

The intended behavior — state verification — is absent. The runner
still constructs state directories, still executes the two-run
transcript against the same directory, and still records a
well-formed report, but `assert_state` was emptied: no data byte and
no journal byte is ever compared, so only exit codes are observed
and every well-exiting implementation passes every case. The package
is inert: it exercises the migration tool and verifies nothing about
the state it produces.

Behavior change: under the reference package the inner pool splits
2 pass / 2 fail; under this variant all four implementations pass,
so the deviation observably changes the outcome (it is not an
equivalent variant).

Freshness: oracle-vacuity was burned at the composition-target
aggregate-gate locus in the predecessor set; the migration scoring
comparison block is a new locus.

deviation: oracle-vacuity @ migration scoring (assert_state compares nothing)
