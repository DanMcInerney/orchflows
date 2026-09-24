# Expected behavior

- **Isolated episodes.** Per-episode state and memory are reset, and concurrent episodes have separate writable fixtures. Evidence shows no shared mutation.
- **Verifiers check change, not a preferred answer.** Verifiers grade the change the agent made against global feasibility, preservation of unrelated commitments, authority limits and required explanations. Any policy-compliant assignment passes, and no task is satisfied by its initial state. Inaction or an empty explanation on an infeasible request fails.
- **Separate credit.** Outcome credit rewards restored sessions, evidence-backed status and usable notices separately from preservation. A useful incomplete outcome can earn high partial credit and still fail full success. Unauthorized changes are critical failures.
- **Admission evidence.** The adversary tries bulk rewrites, doing nothing and claiming success in prose, and fails. Labeled outcomes include a valid alternative, a partial restoration, correct escalation, an unauthorized update, empty output and unavailable judgment.
- **Comparison set.** The agent is compared with a simple baseline at matched budget, or the baseline's absence is explained.
- **Honest provenance.** Variants of the synthetic scenario stay in one source group. The card labels the scenario synthetic, reports its independent realism review, and makes only a bounded development claim.
- **Retained evidence.** Real final states, transcripts, simulator and tool identity, actual overlap, per-episode latency, all launches and unscored outcomes are retained. Local staging is not described as protected isolation.
