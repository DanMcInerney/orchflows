# Design oracle policy

Deterministic rows decide green; visual quality is judged, from
captures only.

| criterion kind | oracle | oracle_class | provenance |
| --- | --- | --- | --- |
| build/type | the workspace's build and typecheck commands | deterministic | pre-existing |
| standards shape | the workspace's linter or formatter | deterministic | pre-existing |
| render integrity | the spec's capture command exits zero at every covered identity with zero error-level console messages | deterministic | pre-existing |
| accessibility floor | the accessibility bar's check command at every covered identity | deterministic | pre-existing |
| visual regression | the spec's diff command against the spec's golden captures; a view with no golden establishes its baseline — establishment is never a PASS, the row decides from the next revision | deterministic | pre-existing |
| design quality | the lens ([lens.md](lens.md)) via `orch-verify`, over fresh captures | judged | authored-here, gate re-verified |

Green means: every deterministic oracle is no worse at the result
revision than at the workspace's recorded baseline, compared by failure
identity and never by count, with every covered identity captured. Loop
policy: the judged row draws only from fresh captures, never a stale
capture.
