# Expected behavior

- Resets per-episode state and memory; concurrent episodes have separate writable fixtures. Evidence shows no shared mutation.
- Grades intended changes, unrelated-state preservation and required explanations. Multiple policy-compliant actions pass; doing nothing without explaining an infeasible request fails.
- Retains real agent final states and transcripts, with simulator/tool identity when applicable. Controls remain distinct from target trials.
- Records actual overlap and per-episode latency, declared resource bounds, all launches and unscored outcomes.
- Makes only a bounded development claim; local filesystem staging is not described as protected holdout isolation.
