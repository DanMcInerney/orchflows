# Research lessons

Use these precedents when choosing search methods; their results do not validate Evolve. Sources were checked September 13, 2026. Evolve's round counts, confirmation protocol and three-case harness test are design choices, not research-derived optima.

| Decision | Precedent and limit |
| --- | --- |
| Patch observed failures and test downstream behavior | [Self-Harness v3](https://arxiv.org/html/2606.09498v3) evaluates harness changes; validation used for promotion is not an untouched final audit. Its tasks do not establish arbitrary artistic evaluation. |
| Justify search complexity and cost | [AIDE² author report](https://www.weco.ai/blog/first-evidence-of-recursive-self-improvement) motivates compact context and mixed exploration. Reward hacking remained; its follow-up did not establish ignition. This is not an independent replication or a ban on tournaments. |
| Choose interventions from traces | [SIA v2](https://arxiv.org/html/2605.27276v2) studies verifier-grounded harness/weight updates. Borrow diagnosis without requiring training; supplied verifiers do not establish inferred artistic preferences. |
| Retain experience across execution periods | [Continual Harness v1](https://arxiv.org/html/2605.09998v1) studies ongoing adaptation in games; it does not establish endless gains or arbitrary live-edit reliability. |
| Check prior successes during adaptation | [Harness Continual Learning v1](https://arxiv.org/html/2608.19013v1) motivates regression-aware adoption. Evolve's known-failure/prior-success/fresh-case set is not statistical sufficiency. |
| Preserve evidence across long development runs | [Harness-of-Harness v1](https://arxiv.org/html/2609.01481v1) keeps its base harness fixed; extended artifact development is not harness self-improvement or matched-cost RSI. |
| Calibrate inferred criteria | [GenRubric v1](https://arxiv.org/html/2608.29856v1) uses training and cross-rubric signals. A spontaneously generated rubric remains a hypothesis, subject to calibration and caller correction. |
| Require artifact-specific judgments | [Judge-reliability research v1](https://arxiv.org/html/2609.02942v1) exposes rubric artifacts. Blinding and reversed-order confirmation do not eliminate shared judge bias; visual transfer is an inference. |
| Keep compact lessons and distinct alternatives | [GEPA v2](https://arxiv.org/abs/2507.19457v2) motivates reflective records and complementary candidates without requiring its optimizer or full transcript history. |

An RSI Level 1 claim under [Weco's taxonomy](https://www.weco.ai/blog/4-levels-of-recursive-self-improvement) requires sustained gains over a strong human-assisted baseline on unseen tasks at matched physical cost. Account for proposals, failures, judges, retries, tools and evaluation; retain a fresh final audit outside selection. Editing a harness alone establishes no level. Evolve has not established RSI Level 1.

Apply the [workflow](../skills/evolve/SKILL.md), [evaluation](../skills/evolve/references/evaluation.md), [harness](../skills/evolve/references/harness.md) and [state](../skills/evolve/references/state.md) contracts for operating rules.
