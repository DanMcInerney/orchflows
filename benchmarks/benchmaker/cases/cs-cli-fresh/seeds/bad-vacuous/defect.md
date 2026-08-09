# bad-vacuous (inert)

The intended behavior — scoring — is absent. The runner still creates
scratch inputs, executes the implementation, and emits a
well-formed report, but its comparison block was deleted: no exit
status is checked, no stdout byte is compared, and every case is
recorded as passing for every implementation. The package is inert:
it runs the csvmerge tool and verifies nothing about it. The manifest,
manifest, case set, and qualification record are all internally
consistent, which is what makes vacuity dangerous — nothing about the
package's static shape reveals that its oracle cannot fail.

Behavior change: under the reference package the inner pool splits
2 pass / 2 fail; under this variant all four inner implementations
pass, so the deviation observably changes the outcome (it is not an
equivalent variant).

Freshness: oracle-vacuity was burned at the composition-target
aggregate-gate locus in the predecessor set; the csvmerge scoring
script is a new locus.

deviation: oracle-vacuity @ csvmerge scoring script (runner comparison block)
