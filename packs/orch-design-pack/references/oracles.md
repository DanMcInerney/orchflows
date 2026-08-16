# Design oracle policy

Deterministic rows decide green; visual quality is judged, from
captures only. Judged rows: [`## Lens`](craft.md#lens).

| criterion kind | oracle | oracle_class | provenance |
| --- | --- | --- | --- |
| build/type | the workspace's build and typecheck commands | deterministic | pre-existing |
| standards shape | the workspace's linter, formatter, or validator | deterministic | pre-existing |
| render integrity | the spec's capture command exits zero at every covered identity with zero error-level console messages | deterministic | pre-existing |
| accessibility floor | the accessibility bar's check command at every covered identity | deterministic | pre-existing |
| visual regression | the spec's diff command against its golden captures; a view with no golden establishes its baseline — establishment is never a PASS, the row decides from the next revision | deterministic | pre-existing |
| design quality | fresh captures at every covered identity | judged | authored-here |

One deviation from [verdict.md](../../../contracts/verdict.md)'s class
policy: a deterministic row is green when no worse than the workspace's
recorded baseline and the spec's golden captures by failure identity,
not only when it passes outright.
