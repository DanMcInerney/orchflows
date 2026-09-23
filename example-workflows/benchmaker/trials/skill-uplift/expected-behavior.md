# Expected behavior

- **Uplift claim.** With-skill and without-skill conditions run the same tasks with the same model, tools, harness and budget. A simple baseline is included, or its absence is explained. Only skill installation differs; the card calls any other difference a whole-system comparison.
- **Activation work.** Tasks include work where the skill should activate and near misses where it should not. Instructions never name the skill. Activation and harm on non-matching work are reported.
- **No teaching to the test.** Tasks resembling the skill's own bundled examples are grouped as exposed or rejected, not counted as independent evidence. The skill is checked for task-specific answers it would leak.
- **Per-task paired results.** Results are per-task paired differences with uncertainty and ties. Tasks where the skill hurts are reported, including the common input variant its wrong instruction breaks, if the suite reaches it. Tasks where the conditions never differ are flagged as low signal.
- **Hard, verifiable tasks.** Tasks are admitted with reference, trivial, audit, adversary and calibration evidence, and deterministic verifiers are used where outputs allow.
- **Scoped claims.** Claims are limited to the harness, model and budget actually run. Cost and time per condition sit beside quality.
