# Design oracle policy

Deterministic rows decide green; visual quality is judged, from
captures only.

| criterion kind | oracle | oracle_class |
| --- | --- | --- |
| build/type | the workspace's build and typecheck commands | deterministic |
| standards shape | the workspace's linter or formatter | deterministic |
| render integrity | the spec's capture command exits zero at every covered identity with zero error-level console messages | deterministic |
| accessibility floor | the accessibility bar's check command at every covered identity | deterministic |
| visual regression | the spec's diff command against the spec's golden captures; a view with no golden establishes its baseline — establishment is never a PASS, the row decides from the next revision | deterministic |
| design quality | the lens ([lens.md](lens.md)) via `orch-verify`, over fresh captures | judged |

Green means: every deterministic oracle exits zero at the result
revision with every covered identity captured. Loop policy: the judged
row draws only from fresh captures, never a stale capture.
