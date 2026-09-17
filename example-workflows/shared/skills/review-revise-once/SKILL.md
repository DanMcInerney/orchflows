---
name: review-revise-once
description: Independently review a stable candidate, make at most one repair pass, and return the reviewed and delivered states with distinct evidence.
disable-model-invocation: true
---

Establish [library context](../../references/library-context.md). Accept the candidate, original requirements, guidance, supporting evidence, review scope, permitted repair scope and checks, output location, and any existing maker handles or fixer settings. Preserve the review input before edits so its identity and evidence remain usable afterward.

Default to one fresh reviewer and at most two child starts: review plus a fresh fixer if needed. A caller may allocate a broader review round or independent repair assignments explicitly; reserve repair allowance before dispatch. When composed, use the assigned allowance and repair arrangement rather than these standalone defaults. No allowance or inability to preserve reviewer independence leaves the dependent work incomplete.

1. Use `orchflows:orch-review` on the identified candidate with its requirements, evidence and Review guidance. Cover the whole result and interactions if review is split. Reviewers report actionable findings and gaps without changing the candidate, repairing or delegating. Gather all outcomes and wait for reviewers to finish before edits.
2. If no actionable repair is justified, retain the unchanged state and actual review coverage, skip repair and continue to verification. Missing review is not a clean verdict. Otherwise make at most one repair pass for supported findings within the permitted scope: continue suitable makers, fix in the caller when its settings permit, or use `orchflows:orch-work` within the remaining allocation. Give each shared cause one owner and pass the gathered findings and Make guidance. Do not silently add a fresh fixer when the caller reserved only direct repair.
3. Run affected checks and the caller's required verification within the remaining bounds. Record the delivered identity, changes, check evidence and unresolved findings. Caller-required independent trial reruns remain separate work in the caller's budget; this component does not launch them automatically.

Return the original reviewed identity and findings separately from the delivered identity and subsequent verification. An unchanged candidate retains its review evidence. A revised candidate has repair verification, not a new independent acceptance. There is no second independent review, repeated repair loop, adoption or external release.
