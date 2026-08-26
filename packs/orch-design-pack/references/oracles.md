# Design oracle policy

| criterion kind | oracle | oracle_class | provenance |
| --- | --- | --- | --- |
| build/type | the workspace's build and typecheck commands | deterministic | pre-existing |
| standards shape | the workspace's linter, formatter, or validator | deterministic | pre-existing |
| render integrity | the spec's capture command exits zero at every covered identity with zero error-level console messages | deterministic | pre-existing |
| accessibility floor | the accessibility bar's check command at every covered identity | deterministic | pre-existing |
| visual regression | the spec's diff command against its golden captures; omitted only when the spec's greenfield discriminator is `true` | deterministic | pre-existing |
| design quality | the lens over fresh captures at every covered identity | judged | authored-here |

One deviation from [verdict.md](../../../contracts/verdict.md)'s class
policy: a deterministic row is green when no worse, by failure identity,
than the reading the cut froze in the criterion at baseline and the
spec's golden captures (verdict.md's evidence clause), not only when it
passes outright.
