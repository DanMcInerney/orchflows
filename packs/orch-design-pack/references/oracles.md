# Design oracle policy

Deterministic rows decide green; visual quality is judged, from
captures only.

| criterion kind | oracle | oracle_class | provenance |
| --- | --- | --- | --- |
| build/type | the workspace's build and typecheck commands | deterministic | pre-existing |
| standards shape | the workspace's linter, formatter, or validator | deterministic | pre-existing |
| render integrity | the spec's capture command exits zero at every covered identity with zero error-level console messages | deterministic | pre-existing |
| accessibility floor | the accessibility bar's check command at every covered identity | deterministic | pre-existing |
| visual regression | the spec's diff command against the spec's golden captures; a view with no golden establishes its baseline — establishment is never a PASS, the row decides from the next revision | deterministic | pre-existing |
| design quality | the lens ([lens.md](lens.md)) via `orch-verify`, over fresh captures | judged | authored-here |

Green is measured at the result revision, over every covered identity,
for the deterministic rows, and at the gate for the judged row,
compared against the workspace's recorded baseline and the spec's
golden captures by failure identity, never by count. Two deviations
from [verdict.md](../../../contracts/verdict.md)'s class policy, which
governs the rest: a deterministic row is green when it is no worse than
that baseline, not only when it passes outright; and the judged row
draws only from fresh captures at the result revision, never a stale
capture.
