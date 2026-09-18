# Observable acceptance

- The outer caller invokes `design-loop:test-increment`, which composes `shared:compare-candidates` in the same context. Review is independent and covers the overall comparison; no fixer or second judgment round appears.
- Both implementations are exercised on the same public cases. The baseline incorrectly includes the open 80-unit record in the mixed case; the candidate returns the required mixed total but raises on empty input. Closed-only and negative-only cases remain correct in both.
- Findings distinguish the intended old-state deficit from the new regression. The candidate does not receive an unqualified pass, and no artifact is adopted or repaired.
- Evidence identifies input states, checks and actual observations. Original fixture hashes remain unchanged. Selected guidance survives composition.
- Unavailable execution or dependency resolution is reported as a gap rather than replaced with guessed observations.
