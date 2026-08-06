# Code oracle policy

All classes deterministic unless a criterion is explicitly judged.

| criterion kind | oracle | oracle_class | provenance |
| --- | --- | --- | --- |
| behavior | the ticket's named test commands | deterministic | pre-existing |
| regression | the full suite the spec names | deterministic | pre-existing |
| build/type | the workspace's build and typecheck commands | deterministic | pre-existing |
| standards shape | the workspace's linter or validator | deterministic | pre-existing |
| readability/design | the lens's shape rubric ([lens.md](lens.md)) via `orch-verify` | judged | authored-here, gate re-verified |

Green means: every deterministic oracle is no worse at the result
revision than at the workspace's recorded baseline, compared by failure
identity and never by count; the judged row is settled at the gate,
fresh from the spec.
