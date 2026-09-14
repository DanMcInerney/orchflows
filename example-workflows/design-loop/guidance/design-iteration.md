# Design iteration

## Make

Choose improvements that move the stated endgoal forward and can be observed. Separate evidence, assumptions and unresolved questions. Prefer a small coherent increment with explicit tradeoffs over a collection of unrelated additions. A first PoC proves the smallest useful end-to-end behavior from the actual starting state.

Use research to reduce a decision-relevant uncertainty. Identify sources and their applicability; the absence of supporting evidence is a gap, not a negative result. For an existing project, preserve known required behavior and the caller's constraints.

Make acceptance criteria inspectable before implementation. Explain how old and new behavior will be compared, including expected feature deficits, regression checks and meaningful limitations. Recommendations should follow the observed results, including failures; do not relabel an untested change as an improvement.

## Review

Assess the exact candidate against its design, endgoal and required prior behavior. Use comparable conditions for old and new states, separate expected new capability from regressions, and distinguish missing evidence from passing checks. Report correctness and meaningful improvement separately. Identify source/state identities and the scope actually examined. Keep findings tied to observations, including partial or unsuccessful results.
