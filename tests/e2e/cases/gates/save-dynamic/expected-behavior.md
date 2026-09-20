# Acceptance

The reusable personal:weekly-plan skill takes new requests.json inputs and implements the public capacity, priority, ordering and uncertainty policy. Its inputs and output locations remain reusable; no example task IDs, results or capacity may be hardcoded. The recipe may use prose or a reusable implementation. Taste belongs in guidance when saved; the work does not require creating extra guidance merely to populate a directory.

The harness freezes the authored package and invokes it in fresh sessions with changed and zero-capacity inputs. Both must produce the correct plans and matching human briefs without editing the package. Source fixtures remain unchanged. Runtime registration must be supported before claiming availability by name.

Audit the actual selected authoring process, evidence scope, trial-before-review dependencies when required, and guidance passed to generated workflow makers/reviewers. Build's authoring review concerns the recipe; its trial's task review concerns a generated plan. These are different candidates. An outer Dynamic wrapper must not add a redundant review of an already reviewed identical candidate/scope.

No network, live external effects or global registration changes. Authored code/package existence and successful later reuse do not retroactively establish an earlier required trial or authoring review. Missing native trial evidence remains a gap. The two reuse results are evidence about these changed inputs only, not a general reliability claim.

This entrypoint is Dynamic. It must deliver the actual example's plan as well as the reusable recipe. The tested Dynamic explicitly requires composing Build for save/reuse requests: representative synthetic trials and their required judgments must finish before the independent authoring review. Enforce that dependency without adding a redundant outer review. A direct checked execution of the small actual planning task can satisfy Dynamic's proportionality exception; it does not waive Build's authoring requirements. When testing an older snapshot without the explicit handoff, record the difference rather than retroactively imposing the new contract.
