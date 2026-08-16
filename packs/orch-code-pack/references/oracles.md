# Code oracle policy

Judged rows: [`## Lens`](craft.md#lens).

| criterion kind | oracle | oracle_class | provenance |
| --- | --- | --- | --- |
| behavior | the ticket's named test commands | deterministic | authored-here when the unit writes the test, else pre-existing |
| regression | the full suite the spec names | deterministic | pre-existing |
| build/type | the workspace's build and typecheck commands | deterministic | pre-existing |
| standards shape | the workspace's linter, formatter, or validator | deterministic | pre-existing |
| readability/design | the lens's shape criteria | judged | authored-here |

One deviation from [verdict.md](../../../contracts/verdict.md)'s class
policy: a deterministic row is green when no worse than the workspace's
recorded baseline by failure identity, not only when it passes outright.
