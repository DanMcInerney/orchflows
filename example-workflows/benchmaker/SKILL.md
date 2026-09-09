---
name: benchmaker
description: Build, independently qualify and empirically calibrate a runnable benchmark for one pinned target configuration.
disable-model-invocation: true
---

Require: `target` (fixed identity), `outcome` (intended observable result),
`sources` (licensed source policy and access/recency limits), evidence-defined
`rigor`, domain construction `standard`, destination `package`, fixed
`target_configuration` and preregistered `calibration_policy` using the
[manifest fields](references/manifest.md). Supply git `workspace`, repository-relative `records`, durable external
`evidence_export`, research evidence-store root, native execution mechanism,
candidate `access_policy`, qualification/reference-audit allocation and total
source/tool/execution bounds. Missing configuration, policy or other required
input returns UNVERIFIED with available artifacts and named gaps before dependent
work; do not infer an experiment from a target name.

    tickets.py frame-open <run> --goal-file <benchmark-goal> --workflow benchmaker

The three private invocations retain this pinned package scope, including
benchmark-quality and benchmark-evidence. Execute each body's contract; a frame
alone is no invocation. Each goal carries original semantic inputs and remaining
bounds. Bind every helper's `workspace` to the supplied construction repository
and `records` to a subtree outside frozen benchmark bytes; `evidence_export`
is the durable locator for a committed record export. Resolve the domain standard in this callee's scope before making.

**Construct.** Supply target/outcome, sources/rigor, standard, configuration/policy,
package/workspace, evidence-store root and bounds to benchmark-construct:

    tickets.py frame-open <run> --parent <frame> --goal-file <construction-goal> --workflow benchmark-construct

Retain the committed draft/design and actual research identities, component
locators, builder contexts and gaps. A construction partial stops dependent work.

**Qualify.** Supply the fixed draft, coverage/rigor, standard, builder identities,
qualification budget, candidate access/protected scope and preregistered
reference-audit sample to benchmark-qualify:

    tickets.py frame-open <run> --parent <frame> --goal-file <qualification-goal> --workflow benchmark-qualify

**Calibrate.** Supply draft and revision-bound qualification, coverage/rigor,
standard, unchanged configuration/policy, native mechanism, access scope,
builder identities, qualification budget, workspace, records/export and remaining
bounds to benchmark-calibrate:

    tickets.py frame-open <run> --parent <frame> --goal-file <calibration-goal> --workflow benchmark-calibrate

Its validity gate owns whether attempts or an evidenced bounded repair can
proceed. Preserve validity, development calibration and separate final
score/drift; required UNVERIFIED never becomes eligibility by omission.

Never: mutate target, optimize/rank/promote configurations, activate results,
substitute controls for agent attempts, disclose protected evidence to candidate
contexts, or revise frozen evaluation after final observations. Development
revisions belong solely to the declared calibration policy.

Return: `tickets.py frame-close <run> <frame> --done <check>` over available
artifact/research identities, manifest, validity and independent findings,
all calibration rounds/decision/ledger, eligible frozen identity when present,
external final-evaluation record or not-performed reason, spend and gaps
(`[]` when none). INVALID/UNVERIFIED/OUT_OF_BAND are useful partial results,
never a qualified calibrated success with required criteria unmet.
