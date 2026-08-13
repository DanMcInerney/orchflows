# Code oracle policy

All classes deterministic unless a criterion is explicitly judged.

| criterion kind | oracle | oracle_class | provenance |
| --- | --- | --- | --- |
| behavior | the ticket's named test commands | deterministic | pre-existing |
| regression | the full suite the spec names | deterministic | pre-existing |
| build/type | the workspace's build and typecheck commands | deterministic | pre-existing |
| standards shape | the workspace's linter or validator | deterministic | pre-existing |
| readability/design | the lens's shape rubric ([lens.md](lens.md)) via `orch-verify` | judged | authored-here |

Green is measured at the result revision for the deterministic rows and
at the gate for the judged row, compared against the workspace's
recorded baseline by failure identity, never by count. One deviation
from [verdict.md](../../../contracts/verdict.md)'s class policy, which
governs every row this clause does not name: a deterministic row is
green when it is no worse than that baseline, not only when it passes
outright.
