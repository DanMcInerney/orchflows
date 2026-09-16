# Benchmarking

## Make

A benchmark estimates performance on a defined class of user work under stated conditions. Exercise the evaluated system's actual model, instructions, tools, orchestration and memory. Reading instructions, unit-testing helpers, or running a simulator establishes no agent capability. Separate harness checks, benchmark validation and agent measurement in every claim.

Prefer a narrow, useful claim and short feedback cycle. Start with representative work and observed failures. Label synthetic scenarios and adversarial oversampling. Families differ in required work, not merely names. Vary meaningful constraints, ambiguity, information location, state transitions and valid strategies. Record source/group identity, provenance, capture dates, transformations and reuse constraints. Verify facts and feasibility.

Choose development/held-out splits before tuning. Keep related variants, shared source documents and templates together when they could leak the claimed generalization. Hold out domains or workflows when the claim concerns them. A small suite without a defensible holdout is a development instrument. Freeze cases, references, scorer, weights and conditions for comparisons; changed definitions create a new benchmark version.

Grade observable outcomes with the least expensive valid method. Deterministic checks fit executable behavior, constraints and state. Anchored human/model rubrics fit qualities without reliable executable definitions. Accept valid alternatives; require a specific trajectory only when it is the capability under test. For stateful tasks check necessary changes, relevant preservation and required explanations. An inert answer does not pass a task that requires an explanation.

Keep mandatory constraints separate from graded quality; style cannot offset a correctness failure. Retain dimension evidence even with binary task success. Validate graders using a checked acceptable outcome, a meaningfully different acceptable outcome where applicable, a plausible near miss, and an empty/inert/shortcut control with explicit expected treatment. Audit a bounded sample independently from public inputs before revealing author answers. Controls establish only the distinctions actually checked; they do not establish empirical difficulty.

For model judging retain rubric, prompt, model/version, order, raw judgment and cited artifact evidence. Calibrate with independently adjudicated examples and report false accept/reject cases and disagreement. Anonymize pairwise candidates, balance order and check swaps on a calibration sample. Keep judge variability separate from agent variability. Permit ties and indeterminate judgments. Missing or unreliable judging leaves the affected metric provisional; never silently substitute string matching.

Inspect rendered/played artifacts in the required modality. Text extraction alone cannot establish layout, image or audio quality. Supplied-corpus research measures work on that corpus; live research includes changing availability. A shortened episode measures that slice, not long-term persistence.

Use the lightest environment that preserves fidelity and needed access controls. Separate solver, simulator, grader and reference roles. Stage only public inputs for the solver. A directory or worktree prevents accidental sharing but does not protect hidden answers from an agent with wider filesystem access; call that local development evaluation. Use an actual access boundary before claiming protected evaluation. Do not remove necessary isolation merely to avoid Docker.

Follow the benchmark contract for budgets, durability, execution statuses and aggregation. Agent budget exhaustion is failure when the budget is part of success. Ordinary provider/setup/grading failures and missing evidence are unscored, with coverage visible. Never improve a score by silently excluding incomplete work or retrying incorrect answers.

Compare conditions on matching cases, resources and budgets, varying only the intended factor for a causal claim. Describe broader changes as whole-system comparisons. Include an incumbent or simple baseline when useful; an oracle is a feasibility control. Interleave or randomize where drift matters. Report per-family quality, per-case deltas/ties, elapsed time and observable usage/cost. Separate cold setup, generation, grading, per-task latency and throughput.

Predeclare repetitions and stopping rules. Average repeats within each case before cases; choose weights before results. A small purposive suite supports descriptive finite-suite results, not a precise population ranking. Match uncertainty analysis to independent case/source groups; keep repeats together. Distinguish task sampling, agent and judge uncertainty. `pass@k` is any success in k attempts; `pass^k` concerns success across all k. Both need repeated-trial evidence and a stated estimator; do not exponentiate a heterogeneous suite mean to claim reliability. No default pass-rate band is required.

## Review

Assess task validity and grader validity independently from target scores. Can the public inputs support an answer? Do controls accept meaningful alternatives and reject near misses or shortcuts? Are source groups, splits and known limitations consistent with the claim? Inspect a sample of actual artifacts/traces, including surprising and unscored outcomes.

Check whether adapters exercise the stated system and whether solver inputs expose evaluator material. Distinguish local staging from enforced secrecy. Look for unobserved modalities, unsupported judge claims, compulsory implementation choices, omitted preservation checks and mandatory failures hidden by quality averages.

Trace result identities, statuses, exclusions, retries, costs and coverage to evidence. Check that resume binds both benchmark and condition, and that changed scorers or conditions cannot silently reuse results. Review bounded overlap, state reset, deadlines and cleanup against executed evidence, naming untested paths. Suppress rankings that missingness or differing coverage could reverse.

Check that another agent can reproduce the delivered commands from declared inputs and dependencies. Report required gaps explicitly; passing harness tests, correct packaging or fluent references cannot establish agent measurement or general benchmark quality.
