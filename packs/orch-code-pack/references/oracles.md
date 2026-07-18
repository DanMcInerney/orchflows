# Code oracle policy

All classes deterministic unless a criterion is explicitly judged.

| criterion kind | oracle | oracle_class |
| --- | --- | --- |
| behavior | the ticket's named test commands | deterministic |
| regression | the full suite the spec names | deterministic |
| build/type | the workspace's build and typecheck commands | deterministic |
| standards shape | the workspace's linter or validator | deterministic |
| readability/design | the lens's shape rubric ([lens.md](lens.md)) via `orch-verify` | judged |

Green means: every deterministic oracle exits zero at the result
revision; the judged row is settled at the gate, fresh from the spec.
