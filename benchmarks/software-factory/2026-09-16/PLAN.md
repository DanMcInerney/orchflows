# Software factory versus one agent

Requested: merge the authored workflow, then build two substantive examples both with it and with a single agent receiving the same prompt.

Merged source: PR #203, commit 1a04d85254455012b9f73e2bced43218f9f755f5. The worktree workflow-source preserves that exact version. No post-result tuning of the workflow or task criteria is planned for the primary comparison.

## Design fixed before builds

Two cases: a secure multi-tenant webhook inbox and a faster fresh log archive with a local staged-release failure exercise. Each has one exact product prompt, common project instructions, identical starter bytes and a separate evaluator. Concrete held-out inputs are not supplied to builders; all tested behavior is specified publicly. Fixture authors do not build candidate solutions.

Each case has two isolated arms. Workflow arm: a fresh coordinator reads the merged software-factory workflow and lets it choose assignments/reviews under its default P=3 bound. Control arm: one fresh agent receives the same product prompt and project context, with no orchflows content and no delegation. Models/effort overrides are left unset for both arms; record what the host makes observable rather than inventing an exact configuration.

Run the two workflow builds first, then the two single-agent builds, as requested. The two independent projects may run concurrently within each wave. Do not transfer first-wave results, reviewer findings or solutions into the single-agent prompts.

Both arms have the same tools and a 45-minute elapsed build limit from their own dispatch. All must preserve user files, write tests/docs and leave a persistent candidate plus evidence. The only different launch instruction selects workflow use versus a single-agent run. Common project context supplies the task/evidence paths and local release policy. There is no live production authority.

Do not expose other-arm work, evaluator source, author conclusions, or intermediate scores to builders. Builders may freely inspect and test their own product. No score-driven repair pass follows final evaluation. Missing/unfinished work is reported; evaluator defects may be corrected only against the predeclared public contract, with the correction logged and both arms rerun identically.

## Evaluation

Run identical external black-box tests after each arm freezes its candidate. Score individual behavior checks and mark security/data failures separately. Run the performance measurements sequentially after all builders finish to reduce load interference; report paired baseline ratios and raw timings. Compare author tests and documentation as supporting evidence, not a replacement for external checks. Record review findings/repairs and whether claims match actual evidence.

Score the log release from the simulator operation log: freeze candidate, pass 10% observations, detect 50% breach, avoid further exposure, restore baseline, verify recovery, report rolled-back status. A webhook run must stop at a human-review handoff. A stub/evasive solution cannot earn a correctness pass by declaring itself blocked.

Record wall time, native child counts and observable model/usage data. This is an end-to-end workflow comparison, not an equal-token or equal-compute experiment: the workflow can spend more agents and resources. Concurrent builds may contend for resources; use timing cautiously. One run per approach per case is descriptive evidence, not a statistical or general reliability claim.

Retain exact prompts, starter/evaluator hashes, artifact identities, raw check outputs, run records and a readable comparison report. Keep generated applications local; the initial PR contains the workflow only.
