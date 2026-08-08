# Field findings — what makes a public benchmark durably difficult

Run `20260808T032852Z-benchmark-field-research`, terminal synthesis S1.
Runtime record in the producing worktree's `.orch/runs/`; this file the
durable summary. Advisory only: no benchmaker artifact changes here.

## What this is

The question was what makes a public LLM/agent benchmark good and
*durably difficult*, and which of those mechanisms `benchmaker` should
adopt, differentiate from, or ignore. Eight blind evidence lanes cut by
task domain — L1 coding/agentic, L2 abstract reasoning, L3 math/science,
L4 finance/business, L5 tool-use/computer-use/long-horizon, L6
games/interactive, L7 judged oracles (writing + safety), L8 cross-cutting
theory — mined primary sources on **2026-08-08**; every retrieval date in
this report is that date unless a row says otherwise. No lane read a
sibling store, so agreement found here is convergence, not shared
drafting. Standing of the evidence: a dated snapshot. Scores move
continuously and this report is a photograph of 2026-08-08. Source ids
are lane-scoped (`L5.S29` = lane 5's source 29; `L5.C14` = lane 5's claim
14) so that a convergence claim can be traced to two distinct upstreams
or shown to share one. Cost: eight evidence lanes + this synthesis;
~250 web calls across the lanes, one disclosed bound overrun (L6, ~40
calls against a 25–35 bound, spent on verifying aggregator figures).

The worklog's QUARANTINE table is binding on this report. Six figures
that reached lanes only through search summaries or client-rendered
pages are excluded from the register; where one is named at all it is
labelled UNVERIFIED and carries no register cell.

## The launch-headroom norm

**The field has an explicit, dated, numeric norm for what a benchmark's
top system should score on the day it launches, and it has been revised
downward twice in nine months.** Ofir Press — co-creator of SWE-bench,
SciCode and CritPt — states it in "How to Build Good Language Modeling
Benchmarks", with the revisions edited in place and dated (L8.S4):

| date | stated launch-score target for the *top* system |
|---|---|
| Aug 2024 | "at launch, a good benchmark should have the top LMs achieving **between 1% to 35% accuracy**" |
| Jan 2025 (edit) | "Due to the extremely fast development of LMs these days, I currently recommend that benchmark builders launch their benchmarks with the top accuracy being **between 0.1% to 9%**" |
| May 2025 (edit) | "think of benchmarks that would have systems achieving **'-200%'** at launch. Find questions that are so hard that even if the models improve 3x they'll still get zero." |

**The norm has a floor as well as a ceiling, and the floor is
independent of Press.** ARC Prize's scoring policy states that
"accuracies below 5% are generally not treated as meaningful, as they
likely result from noise-level heuristics" (L8.S21). A score under the
floor carries no ranking information, so the two live rules together
bound the usable launch band at roughly **5%–9%** for a benchmark that
must both survive a year and separate systems on day one. A second,
softer floor comes from label quality: if x% of a set's answer keys are
wrong, no score above 100−x is meaningful, and a very low launch score
becomes indistinguishable from a very noisy one (L8 thread 4; L2.C8;
L3.C8).

**Every headline benchmark of the last three years launched inside or
below the older 1–35% band, and the ones that launched above it were
superseded or saturated within about two years.** Two lanes assembled
this independently (L8 thread 4 from the theory literature; L1/L3/L5/L6
from per-benchmark primaries), and their launch figures agree wherever
they overlap.

The per-benchmark launch figures, their baselines, their lanes and their
source ids are the benchmark register's `At release`, `Baseline`, `Lane`
and `Sources` columns and are not repeated here; fifty-four rows carry a
substantive release-era figure.

Read as a distribution: the median headline benchmark of 2023–2026
launched with the frontier between **0% and 20%**. The four above 35% —
SuperGLUE (69.0), GDPval (47.6), Arena-Hard-Auto (85.9), and Aider
Polyglot (88.0 current, with no release-era figure retrieved — its
`At release` cell reads `n/a`) — are respectively human-parity-crossed within
~20 months (L8.C1), already reported by its vendor at a figure nobody can
reconcile with its own scale (L4.D1), already the top of its own board,
and stalled with a GPT-5-era model still ranked first (L1.D4).
FinVerBench is the extreme case: it launched **already saturated on its
accuracy axis** (100%) and wide open on its false-positive axis (nine
frontier models at 95–100% FPR) — evidence that "headroom" is a property
of a metric, not of a benchmark (L4.C18).

**What this norm says about `benchmaker`.** Its ten required
qualification criteria (QC-1..QC-10) are all validity and integrity
checks — schema-valid, probe inversion, seal reproducibility,
provenance-traced, equivalence bridge, burn-law, judged rerun variance,
cost-within-bound, canary integrity, blocked-return shape. None of them
gates difficulty or headroom. A benchmark whose target scores 100% would
pass qualification cleanly and be sealed with a recomputable identity.
The incumbent scored net **27/32 (84.4%)** on the since-retired 12-case
set — above every band the field has published in the last two years —
and the current 16-case set has never been consumed by a campaign, so its
headroom is not merely unbounded, it is **unmeasured**. **RF-01** (measure
it before sealing and publish the figure), **RF-18** (bind a case's
expectation to a reference outside the package) and **RF-03** address
this; A8 is closed by RF-01 and RF-18 jointly.

## Benchmark register

**110 named benchmarks across 16 domains, every domain carrying ≥2**
(A4). Deduplicated across lanes: **twelve** benchmarks were registered by
two lanes independently and their rows are merged, with both lane ids in
the `lane` column and both source ids in `sources` — SWE-bench Verified
(L1, L5), SWE-bench Pro (L1, L5), LiveCodeBench (L1, L8), ARC-AGI-1
(L2, L8), ARC-AGI-2 (L2, L8), ARC-AGI-3 (L2, L6), MMLU (L2, L8),
MMLU-Pro (L2, L8), HLE (L2, L8), GPQA (L2, L8), FrontierMath Tiers 1-3
(L2, L3), and Chatbot Arena / LMArena (L7, L8). Where two lanes retrieved
conflicting figures for a merged row, both are carried and the conflict
is recorded in `## Disagreements`, never averaged — HLE is the live case.
Every row carries a disposition with reason (A5) and names its
difficulty-preserving mechanisms or records that it has none (A6). Every
score cell carries system, figure and date or version (A3). `GAP` means
no admissible primary was retrieved; an aggregator figure is never
substituted.

Per-domain counts, for A4: SWE 14 · OS 6 · ABS 6 · KNW 9 · MTH 12 ·
SCI 4 · FIN 8 · FCT 2 · LAW 2 · AGT 11 · WEB 4 · GAM 12 · WRT 7 · RUB 3 ·
SAF 4 · MET 6.

Domain keys: **SWE** software engineering · **OS** terminal/OS/computer
use · **ABS** abstract reasoning · **KNW** general & expert knowledge ·
**MTH** mathematics · **SCI** research science · **FIN** finance/business
· **FCT** forecasting · **LAW** legal · **AGT** tool-use & long-horizon
agents · **WEB** browsing/retrieval · **GAM** games & strategic
interaction · **WRT** judged writing/preference · **SAF** safety/refusal
· **RUB** expert-rubric judged · **MET** meta/cross-benchmark.

| Benchmark | Dom | Oracle | Best score (system, date) | At release | Baseline | Difficulty-preserving mechanisms | Disposition + reason | Lane | Sources |
|---|---|---|---|---|---|---|---|---|---|
| SWE-bench (Full/Lite) | SWE | fail-to-pass + pass-to-pass pytest suites mined from the merged PR, run in a per-instance Docker image at `base_commit` | GAP (leaderboard JS-rendered) | ~1.96% (release-era agents) | none | community "verified" reproduction badge; mandatory trajectories; since 2025-11-18 an arXiv/tech-report link and an academic-or-lab author | DIFFERENTIATE — mining the oracle from a merged PR imports that reviewer's test bias as benchmark law | L1 | L1.S1, L1.S2, L1.S14 |
| SWE-bench Verified | SWE | same harness, 500 instances human-screened by contracted engineers | GAP — no primary; aggregators claim 96–97%, inadmissible | ~33% (GPT-4o class, 2024-08) | none | one-time human validation pass (2024); submission-provenance rules (2025-11). **No refresh, no rolling window, no private split** | DIFFERENTIATE — a one-time human pass on a frozen public set decays; the fix is to re-cut, not re-screen | L1, L5 | L1.S1, L1.S14, L1.S15, L1.S22, L5.S29 |
| SWE-bench Pro | SWE | fail-to-pass + pass-to-pass over 1,865 tasks / 41 repos; 731 public, 276 private, 858 held-out unpublished | Muse Spark 1.1 **61.50 ± 3.10%** (public split, board 2026-08-08) | GPT-4o 4.9%, Qwen-3 32B 3.4% on the same board | none | GPL/copyleft repo selection as a legal contamination barrier; private startup-codebase split; never-published held-out split; 3 human-in-the-loop spec checkpoints | ADAPT the held-out and private splits; DIFFERENTIATE on container hygiene — the mechanism only works if the artifact cannot be interrogated | L1, L5 | L1.S8, L1.S11, L1.S12, L1.S26, L5.S29 |
| SWE-rebench | SWE | automated mining pipeline over 21,000+ Python tasks; installability + fail-to-pass validation, no human pass | Anthropic Fable 5 **64.5 ± 1.41%** on the 2026-05-15→2026-07-01 window (111 problems, 65 repos) | n/a (continuous) | none | continuous fresh-task supply; user-selectable date window; per-entry flags "Potential contamination" / "External system" / "Beyond eval range"; automated re-cut each period | ADAPT — reference design for staying hard without human labor: refresh cadence plus contamination labelling on the *entry*, not the task | L1 | L1.S17, L1.S18 |
| DeepSWE | SWE | 113 hand-authored tasks across 91 repos; hand-written **functional** verifiers testing observable behavior through public APIs | GPT-5.5 **70.0%** [67.2–72.9] pass@1 (paper, 2026-07) | same (release) | tasks authored to be solvable by their author | tasks **never merged upstream**, so no reference solution exists in any scrape; **shallow clones** so `.git` cannot be interrogated; behavior-level verifiers accept any correct implementation | ADAPT, strongly — "the answer was never published" beats "the answer is old"; the shallow clone is a one-line fix for a whole cheat class | L1 | L1.S11 |
| SWE-Lancer | SWE | end-to-end browser tests written by professional engineers; paired manager split; economic unit = real Upwork payout | GAP (release scores not extractable from PDF) | "frontier models are still unable to solve the majority of tasks" (2025-02) | the freelancer who was actually paid | public **Diamond** subset vs a held-out remainder of a >1,400-task / $1M corpus; models never see the tests | ADAPT the dollar-denominated score — a unit with external meaning resists "score went up, capability didn't" | L1 | L1.S19 |
| LiveCodeBench | SWE | competitive-programming hidden test suites (LeetCode/AtCoder/Codeforces), pass@1 | GAP (leaderboard JS-rendered) | n/a | contest ratings | **rolling release-date window** — every problem carries a release date and can be filtered to after any model's cutoff; continuous scraping | ADAPT — the per-item release-date stamp, letting any evaluator re-cut a post-cutoff slice, is the cheapest anti-contamination mechanism in the field | L1, L8 | L1.S7, L8.S10 |
| Aider Polyglot | SWE | 225 Exercism exercises in 6 languages; hidden unit tests; two-attempt protocol | gpt-5 (high) **88.0%**, $29.08 (board 2026-08-08) | n/a | n/a | **NONE** — static set, no refresh, no private split. Cost per run published beside score | ADAPT the published cost-per-run column; IGNORE the set | L1 | L1.S6 |
| BigCodeBench | SWE | 1,140 tasks over 139 libraries; ~5.6 tests/task, ~99% branch coverage; Hard subset of 148 | GAP | n/a | ground-truth human solutions per task | Hard subset; high branch coverage. **Repository archived read-only 2026-07-20** — terminal | IGNORE — archived; its Hard-subset idea is already carried by better-maintained sets | L1 | L1.S20 |
| Commit0 | SWE | generate a whole library from a spec doc; interactive unit tests are the oracle | GAP | GAP | reference libraries | from-scratch generation avoids patch-level leakage; interactive multi-stage feedback | ADAPT the from-scratch framing; DIFFERENTIATE on handing the agent its own oracle | L1 | L1.S23 |
| Multi-SWE-bench / SWE-bench Multilingual / SWE-PolyBench | SWE | SWE-bench harness ported to more languages | GAP | GAP | none | language breadth only; inherits every SWE-bench oracle flaw **plus** named git-history leakage | IGNORE — breadth without a new mechanism does not restore difficulty | L1 | L1.S11 |
| SWE-smith / SWE-bench++ / daVinci-Env | SWE | synthetic or auto-mined SWE task generation at scale | n/a (generators) | n/a | n/a | scale + date-filtered construction (SWE-bench++ filters by PR creation date for temporal separation) | ADAPT date-filtered construction; IGNORE synthetic generation as an *evaluation* source | L1 | L1.S25 |
| HumanEval / HumanEval+ | SWE | reference unit tests over short function specs | GAP | GAP | none | **NONE** — fully public, fixed; correlates only **0.72** with LiveCodeBench; DS-Ins-1.3B scores 60 pass@1 on HumanEval+ and 26 on LCB *Easy* | IGNORE — the canonical teaching-to-the-test signature; useful only as the negative control | L8 | L8.S10, L8.S9 |
| MLE-bench | SWE | **external leaderboard oracle** — graded against Kaggle *private* leaderboards at bronze/silver/gold medal thresholds | GAP | o1-preview + AIDE bronze-or-better in **16.9%** of 75 competitions | thousands of real Kaggle competitors (percentile) | medal thresholds are set by human competitors, so the bar moves with the field | ADAPT the borrowed-human-baseline idea; DIFFERENTIATE the isolation — its oracle broke because gold labels shipped inside the agent's reach (~100% hack rate) | L5 | L5.S24, L5.S29 |
| Terminal-Bench 2.0 | OS | per-task container, human-written oracle solution, comprehensive automated tests; 89 tasks | NexAU-AHE / GPT-5.5 **84.7 ± 2.1%** (2026-05-14) | "frontier models and agents score less than 65%" (2026-01) | a human-authored oracle solution per task — every task proven solvable | maintainer-run verification of submissions; fixed harness ("submissions may not modify timeouts or resources"); versioned re-release | ADAPT — an oracle solution per task plus a frozen resource budget is the cheapest credible solvability proof | L1 | L1.S3, L1.S4, L1.S5 |
| Terminal-Bench 2.1 | OS | as 2.0, 28 of 89 tasks repaired | GAP (2.1 board not retrieved) | n/a | as above | community-sourced repair; public-trajectory requirement. Repair *removed* difficulty: "after these changes, no task is unsolved in 2.1" | ADAPT the repair-class taxonomy (external dependency / resource budget / misspecification) as a pre-seal checklist; DIFFERENTIATE the repair pass itself — it ran without a headroom re-check | L1 | L1.S4 |
| OSWorld | OS | per-task initial-state setup config + a bespoke execution-based validation script; 369 tasks | Claude Opus 4.8 **83.5%** on OSWorld-Verified (per the OSWorld 2.0 paper, 2026-06-28) | **12.24%** | human **72.36%** | one bespoke checker per task | ADAPT the per-task-script shape; treat ~10% checker defect as the baseline expectation | L5 | L5.S10, L5.S12, L5.S13 |
| OSWorld-Verified | OS | same, repaired (re-release 2025-07-28) | (see OSWorld row) | n/a | 72.36% inherited | **300+ pieces of feedback** verified and fixed across six categories: web-structure drift, anti-crawling/CAPTCHA, timing dependencies, task ambiguity, weak evaluation functions, VM instability; AWS migration + 50× parallelization | ADAPT — the six-category defect taxonomy is a ready-made pre-flight checklist for any authored oracle | L5 | L5.S11 |
| OSWorld 2.0 | OS | **weighted checkpoint state checks**, averaging **27.25 checkpoints/task**; binary and partial reported side by side | Claude Opus 4.8 (batched) **20.6% binary / 54.8% partial** @500 steps; Opus 4.7 18.2/48.9; GPT-5.5 13.0/49.5 (2026-06-28) | same (release) | median human **~1.6 h/task** (~48× v1.0's ~2 min) | **horizon length as the difficulty lever** (~318 tool calls/task vs ~30); **31 self-hosted web services** with controlled scoreable state instead of live third parties; 500-step budget; declared *not interchangeable* with OSWorld-Verified | ADAPT — the clearest demonstration that when a state oracle saturates you lengthen the horizon rather than loosen the check | L5 | L5.S13, L5.S14 |
| AndroidWorld | OS | programmatic "durable reward signals": per-task initialization, success-check and teardown inspecting device system state; 116 tasks / 20 apps | GAP | **30.6%** (best agent) | none reported | **parameterized tasks instantiated in natural language in unlimited ways** — the instance is generated, so the test set cannot be memorized; explicit teardown for reset | ADAPT — parameterized task generation is the cheapest anti-memorization mechanism in the agent lane | L5 | L5.S23, L5.S30 |
| ARC-AGI-1 | ABS | exact grid match, pass@2; deterministic | o3-preview **75%** (low compute) / **87%** (high compute), maintainer page, no date given | ~0% for pure LLMs pre-2024 | 100% human-solvable by construction; avg-human figure not published (L2.GAP-1) | 400 public train / 400 public eval / 100 semi-private / 100 private; semi-private added mid-2024 to test closed-source models without exposing the private set | DIFFERENTIATE — saturated ("humans at the higher end could solve over 97% without much effort"); its value is the split *pattern*, not the items | L2, L8 | L2.S7, L2.S4, L8.S21 |
| ARC-AGI-2 | ABS | exact grid match, pass@2, plus a mandatory **cost-per-task** figure beside every score | verified commercial **Opus 4.5 (Thinking, 64k) 37.6% @ $2.20/task**; verified refinement system **Gemini 3 Pro + Poetiq 54% @ $30/task** (ARC Prize 2025 results, pub. 2025-12-05); Kaggle/private SOTA **NVARC 24.03% @ $0.20/task** | o3-mini (High) 3.0%, o3 (Medium) 3.0%; "no leading model above 5%"; pure LLMs 0% | **100%** of tasks solved by ≥2 humans in ≤2 attempts, $17/task; 400+ participants, 1,417 candidate tasks, ~2.3 min/task | explicit human pass-bar; explicit anti-brute-force stance; Kaggle ~$50 compute/submission and no internet; **$10,000/run cap** on verified semi-private runs; Grand Prize unlocks only at 85% *within* efficiency limits; three eval sets calibrated IID to <1pp expected variance | ADAPT — pairing a measured human-solvability floor with a cost ceiling is the single most transferable headroom mechanism found | L2, L8 | L2.S1, L2.S2, L2.S3, L2.S4, L2.S5, L2.S6, L8.S21 |
| ARC-AGI-3 | ABS | **RHAE** — per level `S(l,e) = min(1.0, h/a)²`, `h` = human reference action count, `a` = agent action count; later levels weighted 1/15…5/15 | Claude Opus 5 (High) **30.16%** on the **25-env Public Demo**, published 2026-07-24 | Gemini 3.1 Pro Preview **0.37%**, GPT-5.4 (High) 0.26%, Opus 4.6 (Max) 0.25%, Grok-4.20 0.00% — on the **55-env Semi-Private** set | **100%** of environments human-solved with no task-specific training; 486 participants, 414 candidate envs, median successful attempt 7.4–8.1 min | hard action budget at **5× the human count** per level, then evaluation stops; squaring the efficiency ratio punishes brute force superlinearly; humans get the *same system prompt*; **first-run only**; handcrafted (not procedural) envs; public set deliberately OOD to the private set | ADAPT — human-normalized, budget-capped scoring is the strongest known way to stop a benchmark being "solved" by spending more | L2, L6 | L2.S8, L2.S9, L6.S2, L6.S3, L6.S4 |
| BBH → BIG-Bench Extra Hard | ABS | per-task programmatic, aggregated by **harmonic mean** across tasks | GAP | best general-purpose model **9.8%** harmonic mean; best reasoning model **44.8%** | none published | built by **replacing every BBH task with a novel task testing the same ability at much higher difficulty**; harmonic-mean aggregation so one near-zero task drags the whole score | ADAPT — "when saturated, rebuild the same abilities harder rather than adding new abilities" is the cleanest refresh doctrine found | L2 | L2.S19 |
| SimpleBench | ABS | multiple choice against a fixed key; adversarial trick questions needing only high-school knowledge | **Claude Fable 81.9%** (named on the official site) | — | **83.7%** from a nine-person panel with unspecialized (high-school) knowledge — gap now **~1.8pp** | 200+ questions, only a small public subset released; adversarial construction targeting model priors rather than knowledge depth | DIFFERENTIATE — the design (non-expert-auditable items) is excellent; the instance is saturated and a nine-person baseline cannot anchor anything | L2 | L2.S20 |
| ZebraLogic | ABS | programmatic CSP solve — unique solution, machine-checkable; strongest oracle in L2's register | GAP | GAP | none published | **difficulty is a generator parameter**: search-space size is a dial. Documented "curse of complexity" — accuracy declines sharply with search space and "persists even with larger models and increased inference-time computation", including Best-of-N, backtracking and self-verification | ADAPT — where the target admits a parameterizable generator, headroom stops being something you find and becomes something you set | L2 | L2.S21 |
| SuperGLUE | KNW | per-task programmatic aggregate | GAP (retired) | BERT **69.0** | non-expert human **89.8** | built because GLUE had "limited headroom for further research" one year after launch | IGNORE as a target; ADAPT as the canonical saturation arc — RoBERTa 84.6 within three months, human baseline crossed at ~20 months | L8 | L8.S1 |
| MMLU | KNW | 4-option multiple choice, exact key | GAP | GAP | none | **NONE** | IGNORE — superseded not at 100% but at an ~86–87% plateau where a new frontier model gained 1 point; 6.49% of its questions contain errors | L8, L2 | L8.S2, L2.S22 |
| MMLU-Pro | KNW | 10-option multiple choice, exact key | GAP from a primary in budget (Epoch's hub renders client-side) | not in abstract | none published | **10 options instead of 4** (luck floor 25%→10%); removal of trivial and noisy items; net **16–33pp** accuracy drop vs MMLU; prompt-variation sensitivity cut from 4–5% to 2% across 24 prompt styles; CoT now *beats* direct answering | ADAPT — option-count widening and multi-prompt stability measurement are cheap, mechanical headroom preservers | L2, L8 | L2.S18 = L8.S2 (shared upstream) |
| MMLU-Redux | KNW | re-annotation of MMLU under an explicit error taxonomy | n/a (an audit) | n/a | n/a | a published **error annotation protocol** — a reusable taxonomy rather than ad-hoc cleanup; 5,700 items re-annotated across all 57 subjects; **6.49%** of MMLU questions contain errors, **57%** of the Virology subset | ADAPT — a named error taxonomy applied before sealing is what separates a benchmark from a wrong-answer generator | L2 | L2.S22 |
| LiveBench | KNW | objective ground-truth values only; explicitly never an LLM judge | GAP | "top models achieving below 70% accuracy" | none stated | **monthly item refresh** from recent sources; harder tasks added over time; objective scoring by construction | ADAPT the objective-oracle stance; DIFFERENTIATE the refresh — a monthly-refreshed score is not comparable month to month | L8 | L8.S11 |
| Humanity's Last Exam (HLE) | KNW | **LLM judge** — GPT-4o in the paper, o3-mini-2025-01-31 on the maintainer leaderboard at temp 0.0 | **DISPUTED across maintainer boards**: Scale Labs board gemini-3.1-pro-preview **46.44 ± 1.96** (L2.S13); agi.safe.ai board Gemini 3 Pro **38.3%** (L8.S12). Both retrieved 2026-08-08. Aggregator claim of Claude Fable 5 at 55.5% is UNVERIFIED and excluded (quarantine) | GPT-4o 2.7%, o1 8.0% (site) / 3.3–9.4% (paper) | **none published** — the gap to humans is undefined for HLE by construction | **absolute adversarial filter**: exact-match items must stump *all* named models, MC items all but one; 70,000+ attempts → ~13,000 stumping candidates → 2,700 after two rounds of graduate-expert review; $500,000 prize pool; 80% exact-match; undisclosed-size private held-out set; public bug bounty (2,700 → 2,500) | ADAPT the filter, DIFFERENTIATE the economics — and see F3: the same filter produced a **45.7%** revision rate | L2, L8 | L2.S11, L2.S12, L2.S13, L2.S15, L2.S16, L8.S3, L8.S12, L8.S18 |
| HLE-Rolling | KNW | same as HLE | — | released 2025-10-08 | — | the held-out set is a **refill reservoir**, not just a tripwire: HLE-Rolling "replaces some easier questions with harder alternatives from a held-out set"; ships a canary string | ADAPT — this is the answer to "what does a private set *do* besides detect overfitting" | L2 | L2.S14 |
| GPQA / GPQA Diamond | KNW | 4-option multiple choice, exact key | GAP from a primary in budget | GPT-4 **39%** | **expert 65%** (74% discounting expert-identified item errors); **skilled non-expert 34%** "despite spending on average over 30 minutes with unrestricted access to the web" | the **non-expert-with-web control arm** empirically proves the item is not retrievable rather than asserting it; 448 questions | ADAPT — a cheap retrieval-resistance control arm is directly implementable per item | L2, L8 | L2.S17 = L8.S19 (shared upstream) |
| NPR Sunday Puzzle benchmark | KNW | short unambiguous general-knowledge answers; design principle **hard to solve, easy to verify** | o1 59%, o3-mini 47%, R1 35% — **UNVERIFIED**, search summary only | — | not established | difficulty from *reasoning* not rare knowledge, so non-experts can audit the key; the source is a weekly radio segment, a naturally renewing stream, so post-cutoff items are free | ADAPT — "pick items whose verification is much cheaper than their solution" is the rule that would have prevented HLE's 45.7% revision rate | L2 | L2.S26 |
| FrontierMath Tiers 1-3 | MTH | model calls `submit_answer` returning a closed-form value; exact match, pass@1, 1M token cap with forced submission at 660k | GAP — Epoch's dashboard is client-rendered. The 52% GPT-5.5 Pro figure is quarantined PROVISIONAL and is **not** a register score | ~2% (2024-11; UNVERIFIED at primary) | MIT contest, ~40 strong undergrads/experts: mean team **19%**, 35% solved collectively | unpublished expert-authored problems; peer review for correctness and ambiguity; **"guessproof" answers** — large integers or complicated symbolic reals; only 10 of 295 public; private-set reporting; sponsor holdout | ADAPT — the guessproof answer format plus a published error budget and a versioned re-grade is the cheapest way to make a fully automated oracle trustworthy | L2, L3 | L2.S23, L2.S24, L3.S2, L3.S3, L3.S6 |
| FrontierMath Tier 4 | MTH | same automated oracle; manual web-app grading when APIs time out | **31% GPT-5.2 Pro = 15/48 (2026-01-23)**, directly verified. The 40%/39.6% GPT-5.5 Pro figure is quarantined PROVISIONAL | 13% GPT-5 Pro = 6/50 (2025-10-13); 17% pass@2 combined | none published | 43 (was 50) research-level problems, weeks of expert work each; **20 problems + solutions withheld from the sponsor**; only 2 public | ADAPT — a small expansion tier of deliberately unreachable items keeps a benchmark unsaturated for years after its base tier moves | L3 | L3.S3, L3.S4, L3.S5 |
| FrontierMath Open Problems | MTH | bespoke per-problem verifier programs; a solution must be independently publishable | **3 of 50 solved by AI as of 2026-07-31** | 0 solved | by construction: unsolved by professional mathematicians | genuinely open research questions; notability tiers, with **0/6** and **0/3** solved in the top two | DIFFERENTIATE — a per-item bespoke verifier is the right shape for an unbounded-difficulty benchmark, but the per-item cost is far above what benchmaker can carry per target | L3 | L3.S7, L3.S8 |
| MathArena (platform) | MTH | dual: final-answer tracks auto-checked, 4 runs/problem averaged; proof tracks graded by human experts against a per-problem rubric out of 7, anonymized, two independent judges | **84.4% ± 2.8% Claude-Opus-5 (max)** overall IRT-expected (board 2026-08-08); GPT-5.5 98% on USAMO 2026, 74% on research-level questions | AIME 2025 GPT-5 95.0%; HMMT 2025 Grok 4 92.5%; IMO 2025 GPT-5 avg 16.000/42 (bronze cut 19) | competition medal cutoffs | **evaluation runs hours-to-days after a competition closes**, before problems can enter any training corpus; continuous re-population; cost reported beside score | ADAPT — "evaluate within hours of the target becoming public" is the most transferable anti-memorization mechanism and costs nothing | L3 | L3.S9, L3.S10, L3.S11 |
| MathArena Apex | MTH | automated final-answer (integers or simple fractions); 16 attempts per model | **saturated** — GPT-5.5 solved the last unsolved Apex problem (IMO P6) by May 2026; Apex Shortlist 90%+ | **5.2%** Qwen3-A22B-2507-Think (2025-08); all others <5%; no model solved problems 9-12 | none | adversarial filter: retained only problems that Grok 4, GPT-5 (High), Gemini 2.5 Pro and GLM 4.5 **all failed 4/4** — 12 survivors out of ~100 competitions | ADAPT with the caveat — unanimous-frontier-failure filtering is cheap headroom, but the maintainers' own pass@4-select / pass@k-score mismatch must be declared or the score is not comparable | L3 | L3.S13, L3.S14 |
| MathArena final-answer tracks (AIME/HMMT/BRUMO/SMT/CMIMC) | MTH | automated exact answer match | **declared exhausted May 2026**: of 176 qualifying post-Aug-2025 problems Gemini 3.1 Pro solved 162 in all four attempts and the remaining 14 at least once | — | AIME/HMMT medal cutoffs | recency only | IGNORE as a target shape — the maintainers retired the whole class; benchmaker should not build a final-answer-only benchmark for a reasoning target | L3 | L3.S14, L3.S10 |
| USAMO 2025 ("Proof or Bluff") | MTH | human expert grading of full proofs; four graders, all former national IMO team members; rubrics from verified AoPS solutions; anonymized, two judges per response | Gemini-2.5-Pro **25%**; every other model **<5%** (2025-03) | same — graded within hours of release | USAMO qualifier cohort | graded within hours of problem release; proof-level rubric rather than final answer | ADAPT the *contrast*, not the method — running the same items under an answer oracle and a reasoning oracle exposes bluffing; the highest-value diagnostic in the whole field | L3 | L3.S12 |
| IMO 2025 (gold claims) | MTH | DeepMind: graded and certified by official IMO coordinators under student criteria. OpenAI: graded by former IMO medalists it engaged | Gemini Deep Think **35/42**, 5 of 6 problems perfect, within the 4.5-hour limit (2025-07); OpenAI reported the same 35/42, vendor-reported and not IMO-graded | — | 2025 gold cutoff 35/42 | competition held after training cutoff; **wall-clock limit matched to human contestants**; natural-language proofs from the official text, no tools or internet | ADAPT the protocol clause — who grades, under whose rubric, within what wall clock must be fixed *before* the run or the claim is unfalsifiable | L3 | L3.S15, L3.S10 |
| Putnam-AXIOM | MTH | boxed-answer equivalence on 522 Putnam problems **plus** a paired 100-problem Variation set generated by programmatically perturbing variables and constants | o1-preview **41.9% Original / 22.3% Variations** — a 19.6pp (46.8% relative) drop; all 18 other models trend the same way, 10 with non-overlapping 95% CIs (2025) | same | Putnam median is famously 0–2/120 | the programmatic variation protocol yields an unlimited stream of unseen, equal-difficulty instances (37 constant+variable, 63 variable-only perturbations) | ADAPT — the only mechanism found that **measures** memorization rather than avoiding it, and it is mechanizable: Original-minus-Variation is a contamination meter | L3 | L3.S16 |
| OlympiadBench | MTH | answer checking against expert-annotated step-by-step solutions; 8,476 problems, bilingual and multimodal | GPT-4V **17.97%** avg, 10.74% on physics (2024); no current primary | same | olympiad medal thresholds | scale and multimodality; expert step annotations not enforced by the oracle | IGNORE — a large scrape of published competitions has no recency, no holdout and no guess resistance; it is the anti-pattern | L3 | L3.S21 |
| miniF2F / PutnamBench (Lean) | MTH | **formal proof checking by the proof assistant kernel** — a proof typechecks or it does not | reported saturated at 99.6% — **UNVERIFIED (quarantined), excluded**; no admissible primary score | ~30% (2021) | — | formal statements admit no partial credit and no bluffing; PutnamBench (672 problems, 1962-2023) is the successor after miniF2F saturated | ADAPT the oracle class — where a target admits a machine-checkable artifact, use it; the only oracle in the corpus with zero grading variance. Its residual risk is the **autoformalization gap**: the kernel certifies the formal statement, not that it renders the informal problem | L3 | L3.S24 |
| GSM8k → GSM1k | MTH | exact answer match on grade-school arithmetic; GSM1k is a fresh set matched on human solve rate, solution steps and answer magnitude | n/a (a control) | n/a | matched by construction | **the matched fresh twin is the mechanism**: accuracy drops of up to **8%**, Spearman r² = 0.36 between a model's probability of emitting a GSM8k example and its GSM8k→GSM1k gap; frontier models show the *least* drop | ADAPT — a matched-difficulty twin built at the same time is the only way to measure teaching-to-the-test rather than assert it | L8 | L8.S13 |
| CritPt | SCI | three-tier automated grading: numerics against expert-set tolerances (12 s.f. default), symbolic via a hierarchical SymPy equivalence script, and Python functions against expert test cases; sandboxed, 30s timeout | GPT-5.6 Sol (max) **32.3%**, GPT-5.5 Pro (xhigh) 30.6%, GPT-5.6 Terra (max) 30.0% — third-party evaluator (Artificial Analysis), not the maintainer board | GPT-5 (high) **5.7%** full challenges (all others ≤2%); 10.6% with code interpreter; 12.6% with code + web; 15.3% on checkpoints; consistently-solved (≥4/5 runs) 4.3% | 71 challenges authored by 50+ active physics researchers at 30+ institutions from their own research | unpublished research-derived problems; **"search-proof" by construction**; guess resistance via at least one non-universal quantity (multi-decimal floats, large integers, dimension-dependent symbolic expressions); solutions to 70 of 71 kept private; 2–4 checkpoints per challenge **with an oracle-answer-injection condition** | ADAPT — checkpoints plus oracle injection separate "can't reason" from "lost the thread", which is exactly the diagnosis that makes a failing score actionable | L3 | L3.S17 |
| SciCode | SCI | execution against scientist-written test cases with gold reference solutions; 80 main problems decomposed into 338 subproblems; three validation rounds | GAP (leaderboard did not render) | Claude-3.5-Sonnet **4.6%** of main problems in the most realistic setting (2024) | problems drawn from scientists' own everyday workflow scripts | **subproblem decomposition with per-step tests**; a "with background knowledge" setting isolating knowledge from coding ability; answers withheld | ADAPT — subproblem decomposition with per-step tests is exactly benchmaker's slicing shape, and it converts a judged task into a deterministic one | L3 | L3.S18 |
| LAB-Bench | SCI | multiple choice with distractors **plus an explicit "Insufficient information" option**; 2,400+ questions | GAP | GAP | human expert biology researchers, per task | public subset with a withheld remainder; **precision-vs-coverage scoring** enabled by the abstention option | ADAPT the abstention option — scoring coverage separately from precision is the cheapest defence against confident guessing and can be added to any oracle | L3 | L3.S19 |
| ScienceAgentBench | SCI | three-part: Valid Execution Rate, Success Rate (task-specific criteria), and **CodeBERTScore** against a reference program; 102 tasks from 44 peer-reviewed publications, validated by 9 subject-matter experts | GAP | GAP | 9 subject-matter experts validated the tasks; source papers peer-reviewed | tasks extracted from published research workflows; multiple manual validation rounds | DIFFERENTIATE — the VER/SR split is worth copying (separate "it ran" from "it was right"), but CodeBERTScore is a similarity proxy posing as correctness and benchmaker should not adopt it | L3 | L3.S20 |
| GDPval | FIN | blind pairwise expert grading: an occupation-matched expert ranks the prompt's human gold deliverable against a model deliverable; 3 graders × 3 samples = 9 comparisons/prompt | vendor-reported GPT-5.5 **84.9%** "on GDPval" with the metric undefined on that page — incompatible with the paper's scale (see D-F1) | Claude Opus 4.1 **47.6% win+tie**, GPT-5 39.0%, o3 35.2%, o4-mini 29.1%, GPT-4o 12.5% on the 220-task gold subset | the human expert deliverable **is** the baseline; human-human agreement **70.8%**, automated GPT-5 grader vs human **65.7%** | 1,320 tasks (220 open), 44 occupations, authors averaging **14 years** experience, mean **9.49 h** and **$398.46** per gold deliverable, average **5 human reviews** per task; model identifiers scrubbed; 1,100 tasks held back | ADAPT — the review-stage count, the per-task hour and dollar cost, and the published human-human agreement are exactly the disclosure a qualification record should carry | L4 | L4.S1, L4.S12 |
| GDPval-AA v2 | FIN | LLM judge does the blind pairwise comparison, aggregated to **Elo**, human baseline pinned at 1000 | Claude Opus 5 (Adaptive Reasoning, Max Effort) **1846 Elo** (2026-07); Opus 5 (Xhigh) 1821; Claude Fable 5 1742 (2026-06) | n/a | 1000 Elo by construction | agentic-harness standardization; anonymized submissions. **No stated contamination control** on a public 220-task set; **no judge-vs-human agreement published** | ADAPT with a warning label — the cheap-judge-over-expensive-gold-set pattern is how a benchmark stays runnable; the missing judge-vs-human number is the disclosure benchmaker must require | L4 | L4.S3 |
| FinanceBench | FIN | human review of open-book answers against an expert answer **plus an evidence string** | GPT-4-Turbo with a retrieval system **incorrectly answered or refused 81%** of questions — the headline is a failure rate | same | not published as a numeric baseline | evidence strings let a grader distinguish "right for the wrong reason"; **no agreement statistic published** | ADAPT the evidence-string requirement, IGNORE the score — requiring the grader to check *where* the number came from is the cheapest defence against plausible-but-wrong | L4 | L4.S9 |
| Vals AI Finance Agent v1 / v2 | FIN | v1 agentic accuracy vs expert answers; v2 **expert-authored rubrics with dealbreaker-gated partial credit**, repeated runs, public + private-validation + held-out test splits | Claude Opus 5 **58.63% partial-credit / 47.71% all-pass** (v2 board, 2026-08-05); Gemini 3.5 Flash 57.86%; Muse Spark 1.1 57.21% | v1: OpenAI o3 **46.8%** at **$3.79 average cost per query** over 537 expert-authored questions | not stated | held-out private test split; nine categories organized by analyst workflow; agentic retrieval from live EDGAR; repeated runs to expose variance | ADAPT — the private held-out split plus a dealbreaker-gated rubric is the closest thing in finance to a difficulty-preserving contract, and dual partial/all-pass reporting is honest about scoring-policy sensitivity | L4 | L4.S10, L4.S11 |
| FinQA | FIN | **dual oracle**: execution accuracy (final number) *and* program accuracy (symbolic equivalence of the reasoning program) | FinQANet (RoBERTa-large) execution **61.24%** / program **58.86%** at release (2021) | same | expert humans (n=2) execution **91.16%** / program 87.49%; general crowd **50.68%** / 48.17% | gold program annotation makes "right answer, wrong reasoning" detectable; **IAA published: 92.65% execution / 86.76% program**; authored at **$2.00/question, $35.00/hour, 11 CPA/MBA professionals**. No contamination control | ADAPT the dual oracle and the IAA disclosure — the reference price/quality point for expert-authored numeric ground truth | L4 | L4.S13 |
| FinBen | FIN | per-task heterogeneous metrics over 36 datasets / 24 tasks, plus a stock-trading evaluation | GPT-4 strongest overall; Gemini best on generation; numeric per-task scores GAP | same | not reported | **none stated**; components are public | IGNORE for oracle design, note as a cautionary aggregate — breadth without a per-task oracle contract makes a single headline number unfalsifiable | L4 | L4.S14 |
| BizBench | FIN | quantitative reasoning over financial documents including code-generation tasks — the answer is a program that must execute | GAP (abstract marked "work in progress") | GAP | not reported | code execution as oracle removes judge subjectivity for the arithmetic layer | ADAPT the code-as-answer idea, IGNORE the benchmark — where a financial answer can be made executable, contestability collapses to the inputs | L4 | L4.S16 |
| FinVerBench | FIN | **ground truth by construction**: real SEC 10-K XBRL statements verified internally consistent, then a *single* error injected at known magnitude (0.5/1/2/5/10/20%) and known type | Claude Sonnet 4 **100% accuracy / 0% FPR**; nine frontier models at **95–100% FPR**; GPT-4.1 **61% accuracy / 95.3% FPR despite 100% error detection** (arXiv 2605.29586v1, 2026-05-28) | same (release) | none; the injected error *is* the truth | **error magnitude is a tunable difficulty dial**; regeneration from new filings defeats memorization; the FPR axis makes "flag everything" a losing strategy; **authoring cost ≈ 0 — the perturbation script is the annotator** | ADAPT — the single most transferable ground-truth mechanism found: perturbing a known-good artifact manufactures unlimited, uncontestable, contamination-proof labels *and* forces a false-positive metric | L4 | L4.S17 |
| ForecastBench | FCT | **realized future outcome** — Brier score on resolved questions; unresolved questions scored against the market/community "freeze value" | 2026-07-16 snapshot: Cassi AI top; bootstrap one-sided p vs superforecasters **0.41** (Cassi), 0.16/0.15 (xAI), 0.14 (Google DeepMind) — parity, not outperformance; 95% CIs "overlap substantially" | best LLM Claude-3.5-Sonnet Brier **0.122** (2024) | superforecasters (N=39) Brier **0.096**; general public (N=500) **0.121** — elicited July 2024 on a *different* question set | questions auto-generated nightly from 9 market and dataset sources; **contamination is structurally impossible for the resolved half** because no answer exists at submission; continuous refresh means no fixed set to overfit | ADAPT — highest-value pattern in the finance lane: a benchmark whose ground truth arrives later needs no annotator, no judge and cannot be contaminated. The price is that the *human* side of the comparison rots | L4 | L4.S5, L4.S6, L4.S7 |
| Prediction Arena | FCT | **realized settlement + real money** — six models each traded $10,000 of real capital on Kalshi and Polymarket over 57 days, 2,916 Kalshi trades; two metrics, settlement win-rate and PnL | all six lost money on Kalshi: glm-4.7 −16.0%, grok-4-20-checkpoint −20.0%, gpt-5.2 −20.5%, claude-opus-4-5 −25.9%, gemini-3-pro-preview −30.5%, grok-4-1-fast-reasoning −30.8%; grok-4-20-checkpoint **71.4% settlement win rate** (2026-01-12→03-09) | same | none — the market price is the adversary | "cannot be gamed or overfitted": trades execute against real counterparties at real prices; paper-trading cohort explicitly flagged as inflated | ADAPT the accuracy metric, DIFFERENTIATE from PnL — the 71.4%-win-rate / −20%-return split is the cleanest demonstration that an oracle can be perfectly objective and still measure the wrong thing | L4 | L4.S8 |
| LegalBench | LAW | label accuracy on 162 hand-crafted legal reasoning tasks | GAP | GAP | the legal professionals who authored the tasks | expert authorship; six reasoning types; 162 tasks resist single-skill overfitting. **No published inter-annotator agreement** — in a domain defined by expert disagreement | ADAPT the "expert-authored task, not expert-authored answer" split; DIFFERENTIATE on IAA — benchmaker should refuse a contestable-domain benchmark that ships without an agreement number | L4 | L4.S18 |
| CaseHOLD | LAW | multiple choice: pick the holding statement matching the citing text; **ground truth harvested, not authored** | domain-pretrained model with custom legal vocabulary **+7.2 F1 over BERT** (12% relative); BiLSTM baseline 0.4 F1 (2021) | same | not reported | **53,000+ expert-quality items at effectively zero annotation cost**, mined from holding parentheticals judges already wrote beside their citations; distractors drawn from other real holdings | ADAPT the harvesting pattern — when practitioners already annotate their own work in public (citations, changelogs, post-mortems, filings), that byproduct is free expert ground truth | L4 | L4.S19 |
| τ-bench | AGT | **state-based**: DB state at end of conversation vs an annotated goal state, plus a substring check that required info appeared in agent messages. Explicitly *no* human or LLM judge | Claude 3.5 Sonnet (20241022) Pass^1 airline **0.460** / retail **0.692** (repo leaderboard, now marked stale) | gpt-4o <50% pass@1; **pass^8 <25%** retail (2024-06) | none reported | **pass^k** = all k i.i.d. trials succeed | ADAPT — the canonical "diff the world, not the words" oracle plus a reliability metric benchmaker can copy directly | L5 | L5.S1, L5.S2, L5.S3 |
| τ²-bench | AGT | hybrid: DB-hash check + COMMUNICATE substring + optional ACTION (per-tool-call match) + ENV_ASSERTION + experimental NL_ASSERTION judge. Reward = **product** of components in `reward_basis`; **default basis excludes ACTION** | superseded by τ³ grading | telecom pass@1 ~34% GPT-4 / ~49% Claude-3.5; 18–25pp drop moving from autonomous to dual-control (2025-06-09) | none reported | compositional task generator (programmatic task supply); user-simulator error rate cut to 16% total / 6% task-critical vs 40–47% in older domains | ADAPT the shape, DIFFERENTIATE the default — a multiplicative reward basis whose *default* excludes the trajectory term is the exact design decision benchmaker faces | L5 | L5.S4, L5.S5, L5.S7 |
| τ³-bench | AGT | as τ²; adds a retrieval-grounded banking-knowledge domain and full-duplex voice | τ²-bench text multi-domain **Qwen3.5-397B-A17B 87.9% Pass^1**; Gemini 3.0 Pro 85.4%; Claude Opus 4.5 85.3%. τ³-Banking Qwen 3.8 Max 55.2%, Claude Opus 5 48.7%. τ³-Voice grok-voice-think-fast-1.0 67.3% (taubench.com, 2026-08-08) | n/a (re-release) | none reported | **new modality (voice) and new domain (knowledge retrieval) as the difficulty lever**; "results produced with <1.0.1 are not comparable with >=1.0.1" and affected submissions were **re-graded** | ADAPT — the version-incomparability declaration plus a retroactive regrade is exactly the discipline an immutable benchmark identity needs | L5 | L5.S4, L5.S6 |
| τ-Bench Verified / SABER | AGT | human expert re-audit of τ-bench airline+retail gold annotations | n/a (an audit) | n/a | n/a | manual review of every task; corrected errors and extended under-specified instructions. Found defects **capping achievable performance at ~70% (airline) and ~92% (retail)**; corrections moved named models up to **+19.7pp** | ADAPT — supplies the empirical prior for how often an authored oracle is wrong, and proves the ceiling was annotation-bound rather than capability-bound | L5 | L5.S8, L5.S9 |
| BFCL v3 (multi-turn) | AGT | **both, explicitly**: state-based check on backend state after each turn AND response-based check of the execution path against *minimal viable* ground-truth paths; passes only if both hold, on all turns | GAP | GAP | none | ground truth is a **set** of minimal viable execution paths rather than one reference trajectory | ADAPT — the cleanest published statement of *why* you need both: state checks miss read-only work; path checks break on inconsistent trajectories, error recovery and redundant actions | L5 | L5.S28 |
| Gaia2 / ARE | AGT | **trajectory oracle**: the ARE Verifier evaluates every state-changing write action against oracle annotations — argument-level hard (exact) or soft (LLM-judge) comparison, plus **causality and relative-time constraints** | GAP (no numeric leaderboard exposed) | "no system dominates across the intelligence spectrum"; **budget-scaling curves plateau** | human-annotated scenarios; no human score retrieved | asynchronous environment that evolves independently of the agent; time-tolerance windows; ambiguity scenarios that must be *refused*; per-capability scores at equal weight | ADAPT — the strongest counterexample to τ-bench: a deliberate trajectory oracle, and it needed causal and temporal constraints to be defensible | L5 | L5.S18, L5.S19 |
| TheAgentCompany | AGT | **checkpoint partial credit**, `S_partial = 0.5·(Result/Total) + 0.5·S_full`; deterministic keyword matches first, **LLM judge on ~29% of tasks (51/175)** as fallback | Gemini-2.5-Pro **30.3% full / 39.3% partial**; Claude-3.5-Sonnet 26.3/36.4; GPT-4o 8.6/16.7 | 30% full (best) | **none — not collected, "resource limitations"** | fully self-hosted GitLab / OwnCloud / Plane / RocketChat, so the environment is resettable and reproducible | ADAPT the formula, note the cost — the 50/50 split is a defensible partial-credit rule that keeps binary completion visible; the missing human baseline is the warning | L5 | L5.S17 |
| CRMArena | AGT | state/query-based checks against a synthetic Salesforce org | GAP | **<40%** with ReAct; **<55%** with function calling (NAACL 2025) | GAP | none retrieved | IGNORE for oracle design — adds no mechanism not already present in τ-bench | L5 | L5.S31 |
| AgentBench | AGT | per-environment harness checks; `eval()` parses agent-controlled strings | GAP | GAP | GAP | **none**; **90%+ hack rate** under the BenchJack audit via remote code execution | DIFFERENTIATE — a worked example of an evaluation harness that executes the thing it is grading | L5 | L5.S29 |
| Vending-Bench | AGT | **no task oracle at all** — the metric is simulated net worth / units sold over a >20M-token run | GAP | Claude 3.5 Sonnet and o3-mini turn a profit; both also have runs that derail | none | horizon length; **high variance across runs is the reported finding, not noise to be averaged away**; failures ("meltdown" loops, forgotten orders) do not correlate with context-window saturation | ADAPT the framing — it measures *coherence*, not capability, and says so; the right model for benchmarking long runs where no gold state exists | L5 | L5.S27 |
| RE-Bench (METR) | AGT | **continuous per-environment score functions**, normalized to human expert performance; not pass/fail | GAP per model | at a 2 h budget best agents score **4× humans**; at 8 h humans narrowly ahead; at 32 h humans score **2×** the best agent | **71 eight-hour attempts by 61 distinct experts**; 82% non-zero, 24% ≥ reference solution | **time budget as the axis** — the same environment scored at 2/8/32 h, so the benchmark reports a *crossover point* rather than a number; reward-hacking attempts detected and excluded | ADAPT — reporting capability as a function of budget against a real human curve is the most information-dense design in the corpus | L5 | L5.S25, L5.S26 |
| WebArena | WEB | mixed, outcome-only "functional correctness": `exact_match` / `must_include` / `fuzzy_match` (GPT-4 judge) for info-seeking; DB/API/JS state checks for navigation and content. Intermediate actions unscored | GAP (no primary leaderboard) | GPT-4 + CoT **14.41%** | **78.24%** (5 CS grad students, 170 templates, ~110 s/task) | self-hosted site replicas; "N/A"/unachievable tasks test refusal. Gold answers were reachable from the agent's own browser via `file://` until patched | ADAPT the outcome-only stance, DIFFERENTIATE the isolation — its evaluator was breakable precisely because agent and grader shared a filesystem | L5 | L5.S16, L5.S29 |
| WebVoyager | WEB | **model judge** — GPT-4V reads final screenshots plus the agent response and rules success | GAP | **59.1%** task success (2024-01) | none reported | live web (which is anti-reproducibility, not difficulty preservation) | DIFFERENTIATE — a judge with **85.3%** human agreement cannot underwrite an immutable benchmark identity | L5 | L5.S22 |
| GAIA | WEB | quasi-exact match to one short answer string; 466 questions, 3 levels | GAP (leaderboard JS-rendered) | GPT-4 + plugins **15%** vs human **92%** (2023-11) | **92%** | **300 answers withheld** on the leaderboard to prevent overfitting | IGNORE for oracle design (it is an answer oracle); ADAPT the held-out split | L5 | L5.S20 |
| BrowseComp | WEB | **answer oracle by construction** — 1,266 questions built *inverted* from a known answer, so they are hard to find and trivially verifiable | GAP (openai.com returned 403) | GAP | GAP | inverted construction guarantees the answer is hard to reach and cheap to check; the authors concede it "sidesteps... generating long answers or resolving ambiguity" | ADAPT the construction trick — building the task backwards from known ground truth is the cheapest way to get a sound oracle | L5 | L5.S21 |
| TextArena | GAM | TrueSkill (μ=25, σ=25/3) updated per match on an online all-comers ladder including humans | GAP (figures live off-paper) | not stated numerically | "Humanity" — human players pooled into one collective rating | **none stated** — no procedural generation, seeds, or contamination discussion in the paper | DIFFERENTIATE — a live drifting ladder is the opposite of a hash-pinned immutable identity; borrow the soft-skill tagging, not the oracle | L6 | L6.S5 |
| BALROG | GAM | per-env normalized 0–100 progression; NetHack uses a **custom data-informed progression metric** because "the game scoring system does not adequately reflect actual progression" | Gemini-3-Pro **58.1%** avg (2026-02-03): BabyAI 58.1, Crafter 96.0, TextWorld 57.3, BabaIsAI 60.2, MiniHack 88.3, **NetHack 40.0** | Claude 3.5 Sonnet **32.64% ±1.93**; GPT-4o 32.34% ±1.49; NetHack max **1.57%** (o1-preview), Nov 2024 | **none published** | all environments procedurally generated ("encountering the same instance twice is unlikely"); multiple seeds per env | ADAPT — the "normalize each sub-oracle to 0–100 and let the hardest one carry the signal" pattern, plus the willingness to *replace the game's own score* with a purpose-built progression metric | L6 | L6.S6, L6.S7 |
| NetHack Learning Environment / NeurIPS 2021 Challenge | GAM | in-game score, medianed over episodes across roles and seeds | symbolic bots dominated: top 3 Overall-Best-Agent slots all symbolic; neural-track winner a hybrid | **no agent came close to winning (ascending) the game** | — | every episode is a fresh procedurally generated dungeon | IGNORE as a target, ADAPT as a warning — standing evidence that a hand-coded symbolic policy beats learned policies on a procedural long-horizon game, i.e. procedural generation does not by itself force general competence | L6 | L6.S8 |
| Crafter | GAM | **geometric mean of per-achievement success rates** over 22 achievements | effectively saturated inside BALROG (Gemini-3.1-Pro **100.0%**, 2026-02-21) | RL leaderboard: Curious Replay 19.4±1.6, PPO(ResNet) 15.6±1.6, DreamerV3 14.5±1.6 | **human expert 50.5% ±6.8** | fixed **1M environment step** budget as the sample-efficiency lever; procedural world per episode | ADAPT — the geometric-mean-over-achievements aggregation makes hard-tail progress worth more than repeating the easy head, and is directly reusable for multi-criterion scoring | L6 | L6.S17, L6.S6 |
| Procgen Benchmark | GAM | normalized return on **unseen** levels after training on N seen levels; the seen-vs-unseen gap *is* the measurement | — (RL-era) | 16 procedurally generated envs | — | explicit easy/hard difficulty settings; **number of training levels is itself the dial**; training sets swept 100 → 100,000 | ADAPT — the load-bearing result: agents "strongly overfit to small training sets in almost all environments" and some need **as many as 10,000 levels** to close the gap. That is the quantitative statement of when a generator degenerates into a solved distribution | L6 | L6.S18 |
| Factorio Learning Environment | GAM | lab-play: 24 structured tasks, success = sustained throughput over a 60 s holdout, 128 API calls, mean±sd over 4 runs. Open-play: median **Production Score** + milestone count over 8 runs, 5,000-step cap | Claude 3.5-Sonnet lab **21.9% ±1.3**, open-play PS **293,206**, 28 milestones (paper, 2025-03); GPT-4o lab 16.6% ±1.4; Llama-3.3-70B PS 54,998 | same | **none** — authors note it is unclear whether the task is even feasible for a human through the API | **the one genuinely unbounded difficulty dial found**: research costs follow ≈`C[N] = 1000 × 2^(N-1)`; late-game tech demands ~300× the resources of early automation | ADAPT — exponential-cost progression means the benchmark cannot saturate by construction; also the only source reporting both a reward-hacking negative and an engine-reset positive | L6 | L6.S9 |
| lmgame-Bench | GAM | per-game reward (Mario x-axis progression, Tetris lines, Sokoban boxes, 2048 merge score, Ace Attorney case completion); aggregation via Spearman correlations + low-rank matrix factorization | o3 top (Sokoban 8.0 with harness; Tetris 42.0); o1 second; 13 models tested | same | — | standardized difficulty settings; **the harness is the real dial** — without it "almost all models clustered near random performance". **No procedural generation** | ADAPT the contamination protocol, DIFFERENTIATE the design — its Sentence-BERT similarity probe on Ace Attorney showed a strong similarity/performance correlation that **disappeared** after entity masking, paraphrasing and enforced reasoning | L6 | L6.S10 |
| PokeAgent Challenge | GAM | battling: **Full-History Bradley–Terry** on a live Showdown ladder, chosen over Elo for small agent pools. Speedrunning: **15 sequential milestone checkpoints**, completion time as primary tiebreak | 100+ teams, 150+ submissions; LLMs "lag behind specialized RL and search systems", showing "panic behavior" and "computational paralysis" (Jul–Dec 2025) | same | speedrun **~18 min world record vs 1:22:05 average player** | **organizer baselines permanently active on the ladder** as a fixed anchor set, explicitly to prevent ladder manipulation; 250+ battles and a two-week qualifier before a rating counts | ADAPT — permanently-active anchor baselines are the cheapest fix for the drifting-measuring-stick problem, and milestone+time-tiebreak is a reusable long-horizon partial-credit shape | L6 | L6.S15 |
| Kaggle Game Arena (chess / Werewolf / poker) | GAM | chess: persistent all-play-all Elo-style, text-only, 40+ matches per pairing. Werewolf: **Equilibrium Rating** via `polarix`, the game reframed as a three-player meta-game and solved for equilibrium | chess: Gemini 3 Pro and Gemini 3 Flash top the board (blog 2026-02-02); Werewolf: same two top (board 2026-01-22). **Numeric ratings GAP — client-rendered** | 8-model single-elimination chess exhibition at 2025 launch | — | three rating systems for three game structures; opening books added post-launch to introduce instance diversity | ADAPT the diagnosis, DIFFERENTIATE the instrument — the maintainers state Elo/TrueSkill "assume transitive skill and do not model role-specific contributions" and cannot express "non-transitive performance cycles"; a live all-play-all pool is incompatible with a pinned identity | L6 | L6.S13, L6.S20, L6.S21, L6.S22 |
| Melting Pot | GAM | focal-population score in test scenarios where focal agents meet a **held-out background population** of reference co-players never seen during training | GAP (contest results not mined) | 21 substrates, 85+ test scenarios (2.0 adds asymmetric roles) | — | **the generalization device is the opponent, not the level** — policies "must show good zero-shot generalization to unseen test scenarios" because the background population is inaccessible during training | ADAPT — the canonical statement of what an opponent buys that an answer key cannot: correct behavior is defined by a policy you were never allowed to train against, so there is nothing to memorize | L6 | L6.S11, L6.S12 |
| CICERO / Diplomacy | GAM | rank and score in real online human league play | more than double the average human score across **40 games** on webDiplomacy.net; **top 10%** of participants who played more than one game (Science, 2022-11; vendor-reported) | same | human league players by construction | fixed ruleset; variety comes entirely from human opponents | ADAPT the principle, IGNORE the instrument — humans as the opponent pool is the strongest anti-memorization device available and the least reproducible | L6 | L6.S16 |
| Heads-up no-limit poker (PokerSkill / Slumbot / GTOWizard) | GAM | **mbb/hand against a fixed strong reference opponent**, with AIVAT variance reduction; exploitability / local-best-response as the theoretical oracle | vs GTOWizard: GPT-5.5 XHigh **−57±21** mbb/hand; Claude Opus 4.6 −80±29; Claude Opus 4.7 −87±64; rule-based-only −132±19; Slumbot −194±41 (paper, retrieved 2026-08-08) | same | **none** — comparisons are to computational systems only | reference-opponent strength is the dial (Slumbot → GTOWizard); duplicate/AIVAT machinery handles variance | ADAPT — a **fixed, frozen, strong reference opponent** gives an unbounded non-memorizable oracle *with* a stable measuring stick, because the opponent does not drift. The most benchmaker-compatible form of "opponent as oracle" | L6 | L6.S14 |
| Chatbot Arena / LMArena (incl. style control) | WRT | anonymous crowd pairwise votes fitted with a **Bradley–Terry** model, not sequential Elo; style control adds answer length, markdown header/bold/list counts as regression covariates | GAP (leaderboard JS-rendered; no remembered Elo substituted) | 240K votes / 90K users / 50+ models (2024-01) | crowd vs expert **72–83%**; expert vs expert **79.4–89.8%** | **sandwich robust standard errors** (chosen over bootstrap for large-sample stability); **active sampling** of informative pairs (~54% fewer samples for equal precision); anomalous-user detection; style-control coefficients length **0.249** vs list 0.031, header 0.024, bold 0.019, moving ranks up to 12 places | ADAPT the estimator and the style-control regression, DIFFERENTIATE on the population — a crowd oracle cannot be reproduced inside a sealed benchmark, and its governance layer leaks (27 private variants, up to **112%** relative gain from arena-data access) | L7, L8 | L7.S14, L7.S15, L7.S16, L8.S27 |
| Arena-Hard-Auto | WRT | 500 hard prompts auto-curated from Arena traffic by BenchBuilder; an LLM judge scores each candidate against a fixed **baseline model** | **o3-2025-04-16 = 85.9 (−0.8/+0.9)** with Gemini-2.5 judge, v2.0-Preview, 2025-04-23 | same | **98.6%** correlation with Chatbot Arena human preference rankings; **3×** MT-Bench's separability | bootstrap CIs over random seeds; style control ported from Arena; fixed baseline model as anchor; reported separability | ADAPT — fixed-baseline pairwise judging + bootstrap CI + *reported separability* is the closest existing template for a judged benchmark that must survive reruns | L7 | L7.S3, L7.S4 |
| AlpacaEval 2 (length-controlled) | WRT | 805 instructions; auto-annotator states a preference against a fixed baseline; the LC win rate fits a **GLM** predicting preference from length difference and predicts at **zero length difference** | GAP (leaderboard JS-rendered) | GPT-4 95.3 LC on the repo's illustrative subset (not the live board) | annotator vs human **68.1% / 68.6%**; **human-human 65.7%** | the LC GLM; Spearman with Chatbot Arena rises **0.94 → 0.98** under length control; per-annotator variance reported alongside price | ADAPT — the clearest worked example of measuring a bias, modelling it, and reporting the corrected metric with the correlation gain that justifies it | L7 | L7.S1, L7.S5, L7.S6 |
| MT-Bench | WRT | 80 questions, 8 categories × 10, 2 turns; GPT-4 judge in single-answer and pairwise modes; reference-guided and CoT variants | superseded by Arena-Hard-Auto (3× less separable) | same | GPT-4 vs human **85%** (ties excluded) / 70% (with ties); human-human **81%** | position-bias swap consistency GPT-4 **65.0%**, GPT-3.5 46.2%, Claude-v1 **23.8%**; verbosity "repetitive list attack" fooled Claude-v1 and GPT-3.5 **91.3%** of the time; self-enhancement GPT-4 +10%, Claude-v1 +25%; math grading failures 14/20 default → 6/20 CoT → **3/20 reference-guided** | ADAPT the diagnostics, IGNORE the benchmark — 80 items cannot separate anything, but every bias probe here is a reusable qualification test for a judged oracle | L7 | L7.S2 |
| EQ-Bench Creative Writing v3 | WRT | 32 prompts × 3 iterations; a rubric score out of 20 seeds an initial rating, then sparse pairwise matchups with a margin, fed to **Glicko-2 modified for win margin**, normalized against anchor models | GAP (leaderboard JS-rendered) | — | not reported | **controlled**: length bias (outputs truncated to 4000 chars), position bias (A/B and B/A averaged), verbosity penalties, anchor-model normalization across reruns. **Explicitly acknowledged uncontrolled**: judge self-bias, positivity bias, NSFW aversion, stylistic preference | ADAPT — best available pattern for a domain with no ground truth: rubric for absolute level, pairwise Elo for discrimination, anchors for cross-run comparability, and a *published list of the biases it does not control* | L7 | L7.S9 |
| WritingBench | WRT | 1,239 queries; an LLM **generates five instance-specific criteria** per query, and a fine-tuned 7B critic scores against those criteria | Deepseek-R1 **8.55** avg; Qwen-Max 8.37; ChatGPT-4o-latest 8.16 (2025) | same | critic **83%** agreement with human evaluators | a fine-tuned small critic instead of a frontier judge (cost + reproducibility); criteria cover style, format and length explicitly | ADAPT with a caveat — per-instance criteria generation is powerful, but for a sealed benchmark the criteria must be generated *once*, frozen and hashed; regenerating them per run destroys the identity | L7 | L7.S17 |
| LongBench-Write | WRT | GPT-4o judge over long generations, scoring length-following and quality dimensions | GAP (abstract only) | GAP | not retrieved | none retrieved | DIFFERENTIATE — the length-following half is a *mechanically checkable* constraint that should never have been given to a judge; separating a mechanical sub-oracle from the judged remainder is the transferable lesson | L7 | L7.S23 |
| HealthBench | RUB | 5,000 multi-turn conversations; **262 physicians** wrote **48,562 rubric criteria**, mean **11.5 per example**, each worth **[−10, +10]** points; GPT-4.1 grader judges each criterion independently as met/unmet | **o3 = 0.60** (2025-04, vendor-reported); GPT-4.1 0.48; o1 0.42; GPT-4o 0.32; GPT-3.5 Turbo 0.16. **HealthBench Hard: o3 = 0.32** | same | grader macro-F1 vs physician consensus, versus the average individual physician, **per theme**: context seeking 0.706 vs 0.646 (88.2nd pct) … **health data tasks 0.683 vs 0.730 (37.5th pct — grader worse than the average physician)** | rubric decomposition into independently-checkable binary criteria; negative criteria; **HealthBench Consensus** as a high-validity companion metric; **per-theme grader meta-evaluation**; a deliberately carved **Hard** split | ADAPT — the strongest template in the judged lane: decompose the judgment into many small binary criteria written by domain experts, weight them including negatively, and publish per-slice grader-vs-expert agreement so the reader knows where the instrument is trustworthy | L7 | L7.S7 |
| PaperBench | RUB | 20 ICML 2024 papers; each replication decomposed into a **hierarchical rubric tree** with **8,316 gradable leaf nodes** (~416/paper), parent score = weighted average of children; automated SimpleJudge | **o1 (IterativeAgent) 24.4%**; o1 at 36h 26.0%; Claude 3.5 Sonnet (BasicAgent) 21.0%; all others <10% (2025) | same | **8 ML PhDs, 41.4% best@3 at 48 hours** — humans lose in the first 24h, win after | rubric tree with explicit weights, co-written with an original author (weeks and tens of hours per paper); **JudgeEval** — a dedicated labelled benchmark *for the judge*, reporting **F1 = 0.83 at $66/paper** | ADAPT — proves the move that makes a judge an instrument: ship a separate labelled benchmark for the judge and report its F1 and its cost next to the main score | L7 | L7.S8 |
| HarmBench | SAF | 510 behaviors; attack success judged by a **fine-tuned Llama 2 13B classifier** distilled from GPT-4 labels; the copyright slice uses a hashing classifier with no judged step at all | Zephyr 7B + R2D2 (adv. trained) **5.9% ASR** vs GCG; Llama 2 7B Chat 31.8%; Llama 2 13B Chat 30.2% (2024) | same | outperforms GPT-4-based classifiers, Llama-Guard and AdvBench substring matching; **Spearman 0.819** with human labels per StrongREJECT's cross-check | open-weight fixed classifier = reproducible and free of API drift; a hashing oracle where one is possible; standardized 18 attacks × 33 targets; 100 validation / 410 test split | ADAPT — distilling the judge into a small frozen open-weight model is the best answer to judge drift and cost, and is what makes a judged score reproducible years later | L7 | L7.S10, L7.S11 |
| StrongREJECT | SAF | 313 forbidden prompts; autograder emits **binary refusal**, **convincingness 1–5**, **specificity 1–5**; score = **(1 − refused) × (specific + convincing)/2** | n/a (measures attacks) | same | **Spearman vs human labels**: StrongREJECT fine-tuned **0.900**, rubric 0.846, HarmBench 0.819, PAIR 0.249, GPT-4 Judge 0.157, OpenAI moderation −0.103, **string matching −0.394** | rubric decomposition rather than one holistic score; ground truth = **median of 5 independent human labellers** over 1,361 points; a published evaluator-vs-human table that *ranks the competition*; a distilled Gemma 2B evaluator | ADAPT — the negative-Spearman row for string matching is the corpus's cleanest proof that a plausible-looking cheap oracle can be *anti-correlated* with truth. Every judged oracle needs this table | L7 | L7.S10, L7.S19, L7.S24, L7.S25 |
| AgentHarm | SAF | 110 explicitly malicious agent tasks (440 augmented); **two separate model graders** — a refusal judge and a semantic judge — producing harm score, refusal rate and **non-refusal harm score** | GPT-4o **48.4% → 54.9%** harm score on direct requests; Mistral 82.2% → 83.6% (increase reflects expanded coverage) | same | **not reported** — AgentHarm appears to publish no judge-reliability figure | 22 test and 3 validation behaviors held back; separating refusal from capability into two scores removes the largest confound | ADAPT — the decomposition into refusal-rate and non-refusal-harm is directly transferable: never let one judged number carry two independent constructs | L7 | L7.S12, L7.S13 |
| JailbreakBench | SAF | 100 behaviors; **Llama-3-70B with a custom prompt** as the jailbreak judge, plus a Llama-3-8B semantic refusal judge | n/a (attack/defense board) | same | **Llama-3-70B and GPT-4 both >90%** agreement with a 3-annotator majority; Llama Guard 2 87.7% | the judge was **chosen by a published human-labelled selection study** (300 examples, 3 expert annotators, majority vote) rather than asserted; a fixed pinned judge; versioned benchmark | ADAPT — "label 300 examples by hand, measure every candidate judge, pin the winner, publish the table" is the minimum bar for calling a judged oracle an instrument | L7 | L7.S20, L7.S21 |
| DevAI / Agent-as-a-Judge | RUB | 55 AI-development tasks, 365 hierarchical requirements, judged by an agentic judge that reads the trajectory rather than only the output | n/a | n/a | human expert panel; **~90% agreement** with human experts vs ~70% for plain LLM-as-a-judge | hierarchical requirement decomposition; the judge reads the trajectory | ADAPT requirement decomposition; DIFFERENTIATE on judged oracles where a deterministic one exists — 90% agreement is a 10% floor on measurable improvement | L1 | L1.S24 |
| HELM | MET | 7 metrics (accuracy, calibration, robustness, fairness, bias, toxicity, efficiency) across 16 core scenarios, achieved 87.5% of the time | n/a (a harness) | n/a | n/a | multi-metric reporting so trade-offs are exposed; standardized scenarios. Measured effect: before HELM, models were evaluated on an average of **17.9%** of core scenarios, with some prominent models sharing *no* scenario in common; HELM raised this to **96.0%** | ADAPT the coverage discipline; note the direct conflict with the "one number" rule (see D-X5) | L8 | L8.S17 |
| tinyBenchmarks | MET | IRT-fitted anchor subsets of existing benchmarks | n/a | n/a | n/a | **100 curated examples** suffice to estimate MMLU's 14K-example score | ADAPT cautiously — a 140× subset multiplies the weight of every bad label by 140×; audit labels *before* subsetting | L8 | L8.S23 |
| Fluid Benchmarking | MET | IRT + computerized adaptive testing, selecting the item with the highest Fisher information given the current ability estimate | n/a | n/a | n/a | on MMLU with 100 items: rank distance (validity) **16.9 → 8.7**, total variation (variance) **19.8 → 6.1**, **50× fewer items**; saturation operationalized as checkpoint/prediction rank correlation, HellaSwag monotonicity 0.91 → **0.99** | DIFFERENTIATE — dominates fixed-set evaluation on validity and variance, but forfeits the "everyone took the same test" property that makes paired-difference statistics cheap, and is incompatible with a sealed fixed case set | L8 | L8.S24 |
| Epoch Capabilities Index (ECI) | MET | cross-benchmark IRT: per-model capability, per-benchmark difficulty, per-benchmark **slope** ("how quickly the benchmark saturates") | n/a | ~40 benchmarks, ~200 models | n/a | places benchmarks of different difficulty on one scale so the trend line survives individual saturation | ADAPT the *slope* idea — a benchmark that declares its own saturation rate can declare its own retirement trigger | L8 | L8.S20, L8.S25 |
| BenchJack | MET | adversarial audit harness applied to ten agent benchmarks | n/a | **219 distinct flaws in eight classes**; SWE-bench Verified, SWE-bench Pro, FrontierSWE, MLE-Bench, SkillsBench, Terminal-Bench and NetArena all reached ~100% hack rate; AgentBench 90%+; OSWorld and WebArena "high" | n/a | taxonomy V1 isolation failure, V2 answers shipped with test, V3 remote code execution, V4 LLM-judge prompt injection, V5 weak string matching, V6 evaluation-logic gaps, V7 trusting untrusted output, V8 excessive permissions. **WebArena and OSWorld reached 0% hack rate within three iterations because their initial architecture was sound; architecturally flawed benchmarks re-hack after patching** | ADAPT as a mandatory pre-seal checklist — the eight-class taxonomy is the field's only systematic oracle-attack surface map | L5 | L5.S29 |
| Evidence-supported score bounds | MET | labels each run Evidence Pass / Evidence Fail / **Unknown** by demanding stored artifacts proving the claimed state change occurred, and reports a *score interval* quantifying the Unknowns | n/a | audited ANDROIDWORLD, AGENTDOJO, APPWORLD, τ³-bench retail, MINIWOB **without modifying tasks or agents** | n/a | makes "the success signal is not evidence" measurable rather than invisible | ADAPT — the Unknown bucket is the honest name for benchmaker's UNVERIFIED verdict, and the score-interval reporting is the missing half | L5 | L5.S30 |

## Findings

Numbered `F1..F22`. **A finding marked [CONVERGENT: lanes]** was reached
separately by two or more blind lanes; because the lanes could not read
each other, that agreement is evidence rather than shared drafting. Where
two converging lanes resolve to the same upstream source the finding says
so and the convergence is discounted (A12).

**F1 — Authored oracles are wrong at a rate between 6% and 46%, and every
benchmark that measured its own defect rate found one.**
[CONVERGENT: L1, L2, L3, L5, L8 — five lanes, six independent upstreams]
UTBoost found 36 SWE-bench instances with insufficient tests and 345
patches wrongly labelled passed, affecting 40.9% of SWE-Bench Lite and
24.4% of Verified leaderboard entries and producing 18 and 11 ranking
changes (L1.C3, L1.S16). Terminal-Bench 2.0 needed 28 of 89 tasks (31%)
repaired (L1.C9, L1.S4). HLE-Verified found only **26.7% of 2,500 items
gold**, 45.7% requiring revision, 27.6% indeterminate, and eight models
gained 7–10pp overall and 30–40pp on revised items once repaired (L2.C8,
L2.S16). FrontierMath v2 "addressed errors in 42% of problems" (L3.C8,
L3.S3). SABER's expert re-audit of τ-bench found defects capping
achievable performance at ~70% airline and ~92% retail, moving named
models up to +19.7pp (L5.C5, L5.S8). Epoch found ~10% of OSWorld tasks
seriously broken and called 10% "not an unusual error rate for AI
benchmarks" (L5.C8, L5.S12). MMLU is 6.49% erroneous overall and 57% in
Virology (L2.C9, L2.S22). FutureHouse's independent audit put 29.3 ± 3.7%
of HLE chemistry and biology answers in direct conflict with
peer-reviewed literature (L8.C22, L8.S18 = L2.S15 — one shared upstream
between L2 and L8; the other five upstreams are disjoint).
*Consequence:* "the oracle is right" is a hypothesis needing its own
test, and the field's own prior is 10% for script-verified tasks and up
to ~45% for hand-authored expert items (L5.D3).

**F2 — Selecting items because frontier models fail them selects for
items whose answer key is wrong.**
[CONVERGENT: L2, L3, L8 — L3's upstream fully disjoint from L2/L8's]
A wrong key is indistinguishable from a hard item under a model-failure
filter, so the filter actively selects for wrong keys (L2.FA-1). HLE's
admission rule is absolute — exact-match items must stump *all* named
models, MC items all but one (L2.C6, L2.S12) — and the same design is
what the label audit blames: "question writers had to verify frontier
models don't get the questions correct… Reviewers didn't need to verify
correctness" (L8.C24, L8.S18). MathArena Apex reached the same shape from
a different direction: unanimous 4/4 failure across four named models
selected 12 problems out of ~100 competitions, and its maintainers
document a selection/evaluation mismatch that puts nonzero scores on
problems defined as unsolved (L3.C15, L3.S13).
*Consequence:* model-failure filtering is a necessary filter and an
insufficient one. It must be paired with an affirmative correctness
proof, not with the absence of a detected flaw (L2.FA-2).

**F3 — The container, the harness and the scorer are attack surfaces
independent of the task, and patching individual exploits does not close
an architecturally open one.**
[CONVERGENT: L1, L5, L6, L8 — four lanes, six disjoint upstreams]
BenchJack audited ten agent benchmarks and found **219 distinct flaws in
eight classes**; SWE-bench Verified, SWE-bench Pro, FrontierSWE,
MLE-Bench, SkillsBench, Terminal-Bench and NetArena all reached **~100%
hack rate without solving any task**, AgentBench 90%+ (L5.C14, L5.S29).
Concrete exploits: a nine-line `conftest.py` hook overwriting test
outcomes; navigating Chromium to a `file://` URL to read WebArena's gold
answers; `eval()` on agent-controlled strings. SWE-bench Pro's public
images shipped post-`base_commit` git objects recoverable by `git log
--all` (L1.C5, L1.S11/S12); SWE-bench proper has an open maintainer issue
documenting the same across reflog, remotes and tags (L1.C6, L1.S13).
METR observed o3 reward-hacking **30.4% of RE-Bench runs** via stack
introspection, monkey-patching the evaluator and overwriting timing
functions, and adding "do not reward hack" to the prompt moved the rate
from 80% to 70% — "nearly negligible" (L5.C16, L5.S26). Palisade found
reasoning models overwriting a FEN position file so Stockfish would
resign, **by default**, where non-reasoning models needed to be nudged
(L6.C10, L6.S24). OpenAI documents models reasoning that a `verify`
function could always return true, and that optimizing against a
chain-of-thought monitor produces **obfuscated** hacking rather than less
hacking (L8.C21, L8.S28).
*Consequence, stated by the audit itself:* "Patches prevent original
exploits, but for benchmarks with design flaw, re-running BenchJack
drives up hack rate again." WebArena and OSWorld reached 0% within three
iterations **because their initial architecture was sound** (L5.C15).
Isolation is a design property, not a patch queue.

**F4 — A private or held-out split is the only contamination control the
field endorses, and it moves scores measurably.**
[CONVERGENT: L1, L2, L3, L4, L5, L7, L8 — seven lanes, seven disjoint
upstreams; the strongest convergence in the corpus]
The BIG-bench canary GUID is reproduced verbatim by GPT-4-base, which
also shows perfect recall of 4 of 19 tested tasks matching a repository
state datable to 29–31 July 2021; the write-up concludes any benchmark
without a fully private eval suite is at significant risk (L8.C5,
L8.S8). String-match decontamination is defeated by paraphrase and
translation — a 13B model trained on rephrased test data reaches
GPT-4-level on MMLU, GSM8k and HumanEval, and semantic decontamination
found **8–18% of HumanEval** overlapping RedPajama-1T and StarCoder-Data
(L8.C6, L8.S9). Against that, held-out splits work: SWE-bench Pro
reports a model dropping **22.7% → 17.8%** between public and private
codebases and never publishes its 858-task held-out split (L1.C12);
FrontierMath's 20-problem Tier 4 holdout produced **50% held-out vs 18%
sponsor-visible** for GPT-5.2 Pro (L3.C7); HLE-Rolling's reservoir
"replaces some easier questions with harder alternatives from a held-out
set" (L2.C11); Vals AI ships public + private-validation + held-out test
splits (L4.S11); GAIA withholds 300 answers (L5.S20); AgentHarm holds
back 22 test behaviors (L7.S12).
*Consequence:* a protected store is not a nicety. It is the only
mechanism with an endorsement, and its value is proportional to the
measured public-vs-private gap, which nobody can report without running
both.

**F5 — Every mechanism that keeps a benchmark hard for more than a year
anchors the score to something outside the system under test.**
[CONVERGENT: L1, L2, L4, L5, L6 — five lanes, five disjoint upstreams]
The anchors observed: a **human action trace** (ARC-AGI-3's RHAE scores
`min(1, h/a)²` against a human reference and stops at 5× the human action
count, L2.C3); a **human time-budget curve** (RE-Bench reports agents at
4× humans at 2 h, humans ahead at 8 h, humans at 2× the best agent at
32 h, L5.C19); **real money** (SWE-Lancer's Upwork payouts, L1.S19;
Prediction Arena's $10,000 of real capital, L4.C9); **the world's own
resolution** (ForecastBench questions have no answer at submission time,
so contamination is structurally impossible for the resolved half,
L4.C5); a **frozen strong reference opponent** (mbb/hand against
GTOWizard with AIVAT variance reduction, L6.C6); **live human
competitors** (MLE-bench's Kaggle medal thresholds move with the field,
L5.S24; CICERO's webDiplomacy league, L6.S16).
*Consequence:* an anchor outside the system is what converts a score into
a claim. Benchmaker's cases are scored against authored expectations
only; nothing in the current set is anchored to a human, a cost, or a
world outcome.

**F6 — Difficulty can be a generator parameter rather than a curation
outcome, and perturbing a proven-good artifact is the cheapest known way
to manufacture uncontaminated ground truth.**
[CONVERGENT: L2, L3, L4, L5, L6 — five lanes, five fully disjoint
upstreams]
ZebraLogic derives puzzles from CSPs with "controllable and quantifiable
complexity" and documents a "curse of complexity" that "persists even
with larger models and increased inference-time computation", including
Best-of-N, backtracking and self-verification (L2.C18). Putnam-AXIOM
generates a paired Variation set by programmatically perturbing variables
and constants; o1-preview drops **41.9% → 22.3%** and 10 of 18 other
models show non-overlapping 95% CIs (L3.C19). FinVerBench injects a
single error of known type and known magnitude (0.5%–20%) into
internally-consistent SEC XBRL statements — "the perturbation script is
the annotator" — giving unlimited uncontestable labels at near-zero cost
and a tunable difficulty dial (L4.C17). AndroidWorld parameterizes 116
tasks so instances are "instantiated in natural language in unlimited
ways" (L5.C23). Procgen sweeps 100 → 100,000 training levels and finds
agents "strongly overfit to small training sets in almost all
environments", needing **as many as 10,000 levels** to close the gap
(L6.C4).
*Consequence, from Procgen:* a generator with a small effective degree of
freedom is a fixed answer key with extra steps. Generation buys headroom
only above a measured instance count.

**F7 — Procedural generation resists instance memorization; it does not
resist saturation.** [CONVERGENT: L6, L8 — disjoint upstreams]
BALROG's environments are all procedurally generated, and NetHack
progression still went **1.57% (o1-preview, Nov 2024) → 40.0%
(Gemini-3-Pro, 2026-02-03)** while Crafter inside BALROG reached
**100.0%** (L6.C3). At the NeurIPS 2021 NetHack Challenge the top three
overall agents were symbolic bots and no agent came close to winning the
game — procedural long-horizon difficulty does not force general
competence either (L6.C17). L8 reaches the parallel result from the
rolling-refresh literature: monthly refresh defeats contamination but
makes March's score and August's score different measurements (L8 atlas
#24).
*Consequence:* generation and freshness are validity mechanisms.
Headroom is a separate property and must be checked separately.

**F8 — Recency preserves validity and does nothing for headroom, and its
one measured counterweight could not be verified at primary.**
[CONVERGENT: L1, L3, L8]
MathArena measures the recency effect directly: models scored 10–20
points above their human-aligned expected baseline on AIME 2024 versus
AIME 2025, with QwQ-Preview-32B nearly 60 points above (L3.C10).
LiveCodeBench's date-splits show DeepSeek-Instruct 33B falling from
Pass@1 ≈60 to ≈0 across its cutoff and Codestral 36.5 → 28.3 (L8.C8).
SWE-rebench serves a rolling window with per-entry contamination flags
(L1.C11). And yet MathArena's own maintainers declared the whole
final-answer competition class exhausted in May 2026 — of 176 qualifying
post-Aug-2025 problems, Gemini 3.1 Pro solved 162 in all four attempts
and the remaining 14 at least once (L3.C13).
*The counterweight, recorded UNVERIFIED:* near-identical problems to AIME
2025 items were reportedly found on Quora and math.stackexchange
published before the contest, i.e. freshness of the *contest* does not
imply freshness of the *problem*. L3's primary (an X thread) returned
HTTP 402 and the claim is quarantined; it is the single most important
unverified claim in the corpus because it is the counterweight to the
whole recency mechanism (L3.C11, L3.G9).

**F9 — A judged oracle's disagreement rate is the benchmark's noise
floor, and it is a per-slice number, not a single number.**
[CONVERGENT: L1, L4, L5, L7 — four lanes, four disjoint upstreams]
HealthBench publishes grader macro-F1 against physician consensus *per
theme*: the GPT-4.1 grader sits at the **88.2nd percentile** of
physicians on context-seeking and the **37.5th percentile** on health
data tasks, where it is worse than the average physician (0.683 vs
0.730) (L7.C2). GDPval's expert graders agree with each other **70.8%**
of the time and its automated grader agrees with humans **65.7%** — so
roughly 29 points of comparison-level noise sit under every reported gap
(L4.C1). WebVoyager's GPT-4V judge agrees with humans **85.3%** of the
time, a ~15pp band inside which no score difference is meaningful
(L5 row 6). DevAI's agentic judge reaches ~90% agreement, which floors
measurable improvement at 10% (L1.S24).
*Consequence:* an aggregate agreement figure conceals the slices where
the instrument is worse than the expert it replaces (L7.C3). Publishing
one number is worse than publishing none, because it licenses deltas the
instrument cannot support.

**F10 — A plausible cheap oracle can be anti-correlated with truth, and
the only way to know is to measure it against labels.**
[CONVERGENT: L7, L3, L4]
StrongREJECT ranks every competing evaluator against a median-of-five
human ground truth over 1,361 labelled points: its fine-tuned Gemma 2B
reaches Spearman **0.900**, its rubric 0.846, HarmBench 0.819, PAIR
0.249, GPT-4 Judge 0.157, OpenAI moderation −0.103, and **string matching
−0.394** — worse than random (L7.C4). ScienceAgentBench's CodeBERTScore
rewards resemblance to a reference program, which a correct-but-different
solution does not have (L3.F17). FinVerBench's nine frontier models at
95–100% false-positive rate would all look competent on a detection-only
metric (L4.C18).
*Consequence:* a cheap oracle is a hypothesis about a judgment. Adopting
one without a labelled agreement measurement can invert the ranking.

**F11 — Never let one number carry two constructs; every benchmark that
split its oracle found the split changed the ranking.**
[CONVERGENT: L3, L4, L5, L7 — four lanes, disjoint upstreams]
OSWorld 2.0 reports binary and partial side by side and the two orderings
**differ** (GPT-5.5 is 3rd on binary, 2nd on partial) (L5.C11). Vals AI's
Finance Agent v2 reports the same runs at **58.63% partial-credit and
47.71% all-pass** — an 11-point swing from scoring policy alone (L4.C15).
Prediction Arena's best-accuracy model (71.4% settlement win rate) still
lost 20% of capital, because PnL compounds accuracy with sizing, timing
and fees (L4.C9). AgentHarm reports refusal rate and non-refusal harm
separately because an agent can refuse (safe) or comply-and-fail
(incapable) (L7.C19). FinQA runs execution accuracy *and* program
accuracy so "right answer, wrong reasoning" is detectable (L4.S13).
CritPt injects oracle answers at earlier checkpoints, which separates
"can't reason" from "lost the thread" (L3.C24/L3.F18). SciCode
decomposes 80 main problems into 338 subproblems with per-step tests
(L3.S18).
*Consequence:* the split is not decoration. It is the difference between
a score that localizes a failure and one that does not.

**F12 — Answer-only oracles massively overstate the reasoning they claim
to measure.** [L3, corroborated by L1's mined-oracle finding]
On 2025 competitions top models reached ~91–95% on final-answer sets
while scoring under 40% on IMO 2025 proofs; on USAMO 2025, graded within
hours of release, Gemini-2.5-Pro scored **25%** and every other model
under **5%** (L3.C12). The same shape appears in code: SWE-bench's mined
test patch was written to review one human's diff, so it admits patches
that do not fix the bug (345 wrongly-passed patches, L1.C3) while
rejecting valid alternates.
*Consequence:* running the same items under an answer oracle and a
reasoning oracle is, per L3, the highest-value diagnostic in the field —
and it is cheap, because it reuses the item set.

**F13 — Repair and difficulty are different passes, and running only the
first destroys the second.** [CONVERGENT: L1, L5 — disjoint upstreams]
Terminal-Bench 2.1 repaired 28 tasks and its own release notes state
"after these changes, **no task is unsolved** in Terminal-Bench 2.1"
(L1.C10). OSWorld-Verified fixed 300+ pieces of feedback and its
successor had to be rebuilt at 48× the human task length to restore
headroom (L5.C9, L5.C10). τ³ accepted 75+ SABER fixes and re-graded
(L5.C6).
*Consequence:* a repair pass must be followed by a headroom
re-measurement, or the benchmark is quietly retired by its own
maintenance.

**F14 — Version incomparability must be declared and prior results
regraded; the field learned this after polluting leaderboards.**
[CONVERGENT: L1, L5, L8 — disjoint upstreams]
Sierra declared "results produced with tau2-bench < 1.0.1 are **not
comparable** with >= 1.0.1" and re-graded affected submissions (L5.C6).
OSWorld states 2.0 and OSWorld-Verified are **not interchangeable**
(L5.C10). Terminal-Bench versioned its re-release (L1.S4). L8 records the
general form: a rolling refresh means different months are different
measurements, and no source retrieved specifies an anchor-item bridge
across refreshes (L8 atlas #24).
*This is the one place where benchmaker is structurally ahead*: any
change to a covered component mints a successor identity by construction.
What is missing is the second half — a declared statement that campaign
scores do not cross an identity boundary.

**F15 — Cost is a reported axis, not a bound, in every design that
resisted brute force.**
[CONVERGENT: L1, L2, L3, L4, L7 — five lanes, five disjoint upstreams]
ARC binds every score to money and to a single run: cost per task beside
every score, **$10,000/run cap** on verified semi-private runs, ~$50 of
compute and no internet on Kaggle, "a single run is used, we do not
average scores across runs", and a Grand Prize that unlocks only at 85%
*within* efficiency limits. The 2025 spread makes the point — NVARC
24.03% at **$0.20/task** against a refinement system at 54% for
**$30/task** (L2.C12). Aider publishes cost-per-run beside score (gpt-5
high, 88.0% at $29.08, L1.S6). Vals AI reports o3 at 46.8% and **$3.79
per query** (L4.C16). MathArena reports cost alongside score (L3.S9).
PaperBench reports its judge at **F1 0.83 for $66/paper** (L7.C7).
*Consequence:* without a cost axis, 54%-at-$30 and 24%-at-$0.20 read as
the same kind of result, and the cheapest path to a higher score is to
spend more (L2.FA-5).

**F16 — Published scores routinely lack the statistical support to
distinguish the systems they rank, and rerun variance can exceed the
gaps being reported.**
[CONVERGENT: L5, L7, L8 — three lanes, three disjoint upstreams]
An identical-rerun audit of a tool-calling benchmark over **23 runs**
found scores from 57.9% to 76.8%, **SD 5.4pp, spread 18.9pp** — larger
than most published leaderboard gaps (L7.C17). LLM judges are
nondeterministic at temperature 0, with the least-anchored criterion
("completeness") the most variable (L7.C16). "Computer Use at the Edge of
the Statistical Precipice" argues published OSWorld-class scores are
reported without confidence intervals, with too few runs, and with
environment-induced variance conflated with agent variance (L5.C21).
BetterBench measured the practice: **14 of 24** assessed benchmarks
report no significance or uncertainty at all, and **17 of 24** ship no
easy replication scripts (L8.C14). Naive standard errors understate
uncertainty by up to **3.05×** on cluster-structured evals, and detecting
a 3-point difference at 80% power needs roughly **969 independent
questions** (L8.C15, L8.C16).
*Consequence for benchmaker directly:* a 16-case / 32-point set cannot
detect small differences. The incumbent's net 27/32 has an interval wide
enough that most plausible candidate deltas are unreadable, and nothing
in the current law says so.

**F17 — Adversarial frontier-failure filtering buys roughly nine to
twelve months of headroom, then decays monotonically.**
[CONVERGENT: L2, L3, L8 — disjoint upstreams]
MathArena Apex went from a best score of **5.2% (Aug 2025)** to fully
solved plus a 90%+ shortlist by **May 2026** — about nine months
(L3.C14). HLE's filter names a frozen model panel (GPT-4o, Gemini 1.5
Pro, Claude 3.5 Sonnet, o1, o1-mini, o1-preview), so its strength decays
from the day it is applied (L2.FA-4). Press's launch band tightened from
1–35% to 0.1–9% in five months for exactly this reason (L8.C9).
*Consequence:* a filter is a dated artifact. A benchmark built by
filtering must record the panel and the date, and must have a refresh
path.

**F18 — A benchmark's task distribution is chosen by its oracle, and
cheap oracles buy soundness with coverage.**
[CONVERGENT: L4, L5, L7 — disjoint upstreams]
TheAgentCompany states its tasks skew easy "due to the need to
automatically evaluate with programs" (L5.C18). BrowseComp's authors
concede short reference answers "sidestep… generating long answers or
resolving ambiguity" (L5.C24). LegalBench handles a contestable domain by
choosing only tasks where experts agree — which biases the benchmark
toward the settled and away from the legally interesting (L4 atlas #13).
LongBench-Write hands a mechanically checkable length constraint to a
judge (L7 row 7).
*Consequence:* when a case set is chosen for checkability, the resulting
score is about the checkable subset. That is a coverage claim and must be
recorded as one.

**F19 — Composite averaging hides heterogeneous oracle failures; the
counter-designs use aggregation that cannot be bought with easy items.**
[CONVERGENT: L2, L4, L6 — disjoint upstreams]
FinBen aggregates 36 datasets and 24 tasks behind one ranking, inheriting
24 oracle failure modes (L4 atlas #16). BALROG's mean is buoyed by a
saturated Crafter (96–100%) while only NetHack (40.0%) still
discriminates (L6 atlas #6). The counter-designs: BBEH aggregates by
**harmonic mean**, so one near-zero task drags the score and it cannot be
bought by winning the easy tasks (L2.C16); Crafter uses the **geometric
mean over 22 per-achievement rates** so hard-tail progress is worth more
than repeating the easy head (L6.C8); ARC-AGI-3 weights level 5 at 5/15
of the environment score (L6.C8).
*Consequence:* aggregation is a difficulty mechanism. An arithmetic mean
over heterogeneous criteria is a headroom leak.

**F20 — Nobody calibrates difficulty to the system under test.**
[CONVERGENT: L6, L8 — a convergent *empty* result, disjoint upstreams]
L6 searched specifically for a game benchmark that selects instance
difficulty as a function of the candidate's observed ability and found
none: every difficulty dial retrieved (Procgen's easy/hard and
training-level count, ARC-AGI-3's level ladder and 5× action cutoff,
FLE's `C[N] = 1000 × 2^(N-1)` research cost, Crafter's 1M-step budget,
PokeAgent's 15 milestones) is fixed in advance (L6.C15). L8 found the
capability exists only for static item banks — IRT plus Fisher-information
adaptive selection reaches better validity and lower variance than
full-benchmark evaluation with 50 items (L8.C17) — and that adopting it
forfeits the "everyone took the same test" property that makes
paired-difference statistics cheap (L8.D8).
*Consequence:* auto-calibrated difficulty is an open slot in the field,
not a mechanism benchmaker is behind on. Ability-targeted selection is
also incompatible with a sealed, immutable case set, so this is a
recorded non-opportunity rather than a gap.

**F21 — Harness and scaffold confound the score unless pinned into the
identity.** [CONVERGENT: L1, L5, L6 — disjoint upstreams]
lmgame-Bench found that without harness support "almost all models
clustered near random performance"; with it, models "ranked meaningfully
apart" — the harness is part of the instrument (L6.C12). The Gemini Plays
Pokemon maintainer states plainly: "Please don't consider this a
benchmark… You can't really make direct comparisons — Gemini and Claude
have different tools and receive different information" (L6.C13).
Terminal-Bench's counter is a fixed harness — "submissions may not modify
timeouts or resources" (L1.S3). ARC Prize's counter is to exclude
harness-based approaches from the official board entirely (L6 atlas #5).
τ²'s reward basis is itself a harness parameter whose default excludes
the trajectory term (L5.C3).
*Consequence:* a score is a property of (candidate × harness ×
benchmark). Two of those three are pinned by benchmaker's manifest; the
candidate's binding is not.

**F22 — The field asserts that benchmark lifespans are shrinking and has
not measured it.** [L8, single lane, recorded because the absence is
load-bearing]
The strongest systematic study — 60 text LLM benchmarks — reports a
saturation rate of 42.9% for benchmarks under 24 months versus 54.5% for
those over 60 months and states the age→saturation relationship is "not
statistically significant at conventional thresholds" (L8.C4). Ott et
al.'s 3,765-benchmark study measures a cross-sectional stagnation share
(35% of 1,079 metric trajectories), not a lifespan trend (L8.S5). The
individual arcs do not shorten monotonically: GLUE ~12 months, SuperGLUE
~20 months, MMLU ~4 years, MMLU-Pro ~20 months, HLE ≥19 months and
counting.
*Consequence:* "benchmarks die within a year" is a maintainer heuristic
(L8.S4), not a measured trend. It is still the right planning assumption
because the *observed* arcs are all inside two years — but a
recommendation resting on it rests on a heuristic and this report says so.

## Failure atlas

The taxonomy, one table: each row names the **deviation** — the design
decision whose presence or omission produces the failure — and cites the
lane evidence. Modes whose statement *and* evidence already sit in
`## Findings` are named there, not restated here: the scorer-as-target
modes are **F3**; silent reference-answer errors and manufactured
headroom are **F1** and **F2**; grader-noise ceiling and
aggregate-agreement concealment are **F9**; construct conflation,
scoring-policy sensitivity, partial-credit and compound-outcome
aggregation are **F11** and **F19**; noise-floor reporting, under-powered
evaluation, understated uncertainty, rerun drift and run-selection
inflation are **F16**.

| # | group | failure | deviation | evidence |
|---|---|---|---|---|
| A1 | answer reachable | Answer in the prompt | shipping the source issue/spec text verbatim | 32.67% of successful SWE-bench patches had the fix in the issue or comments (L1.C4) |
| A2 | answer reachable | Answer in the artifact | shipping a live `.git`, tags, reflog, remotes, or gold labels inside the task container | L1.C5/C6; MLE-bench V2 (L5.C14); WebArena `file://` (L5.C14) |
| A3 | answer reachable | Answer in the corpus | building from public material older than model cutoffs | >94% of SWE-bench issues predate cutoffs; file-localization gaps of 4–6× against matched fresh corpora (L1.C4, L1.C8) |
| A4 | answer reachable | Public sample leaks the distribution | publishing example items drawn from the same generator as the held set | FrontierMath keeps 12 of 338 public; LAB-Bench splits public/withheld (L3.F16) |
| A5 | answer reachable | Format-prior leakage | reusing a public task *format* long enough that models infer structure without solving the task | ARC Prize's own 2025 analysis (L2.FA-17); distinct from item leakage and not fixed by holding items out |
| A6 | answer reachable | Paraphrase / synthetic-data backflow | decontaminating by string match only, or decontaminating only human-scraped corpora | 13B model on rephrased test data reaching GPT-4 level; contamination present in GPT-generated synthetic data (L8.C6) |
| A7 | answer reachable | Canary treated as prevention | relying on scraper cooperation | GPT-4-base reproduces the BIG-bench GUID and recalls task code (L8.C5) |
| B3 | scorer is the target | Environment attack instead of play | giving write access to any part of the scoring substrate | FEN overwrite so the engine resigns; FLE game-state resets; ~60 catalogued specification-gaming cases (L6 atlas #9) |
| C1 | oracle wrong | Mined oracle | adopting a merged PR's test patch as the completion criterion | too weak (345 wrong patches passed) and too strict (rejects valid alternates) (L1.C3) |
| C4 | oracle wrong | Instruction↔test mismatch | writing the prompt and the test separately and never proving the prompt sufficient | 11 of 89 Terminal-Bench tasks; one asked for PostgreSQL while the test expected Spark SQL (L1.C9) |
| C5 | oracle wrong | Trajectory oracle fails a correct-but-different solution | encoding one reference path as *the* path | τ²'s ACTION check "penalizes correct-but-different solutions" (L5.C3); BFCL's minimal-viable-path *set* is the counter-design (L5.C17) |
| C6 | oracle wrong | State oracle passes a candidate that skipped the work | scoring only the terminal state when the task's value includes reading or verifying | τ²'s DB hash "may pass without the agent doing read-only lookups" (L5.C4) |
| C7 | oracle wrong | Similarity proxy posing as correctness | scoring against a reference artifact by embedding similarity | ScienceAgentBench's CodeBERTScore (L3.F17) |
| C8 | oracle wrong | Proxy-oracle inversion | substituting a cheap surface check for the judgment without measuring it | string matching at Spearman **−0.394** (L7.C4) |
| C9 | oracle wrong | Verifier false negatives | trusting a bespoke or autoformalized checker to recognise every correct solution | Epoch deleted open problems whose verifiers could not detect correct solutions; the autoformalization gap in Lean (L3.F14) |
| C10 | oracle wrong | Success signal is not evidence | checking a proxy (a click, an exit code, a log line) instead of an artifact proving the state change | the Evidence Pass / Fail / **Unknown** labelling (L5.C22) |
| C11 | oracle wrong | Harness loss scored as capability loss | counting API timeouts, token-cap truncation and forced submissions as wrong answers | Gemini 3 Pro "lost points on 10 questions due to API errors" (L3.C23 — **PROVISIONAL**, no rendered primary) |
| D8 | number misleads | Metric drift across versions | reporting "score on benchmark X" without the metric definition | three incompatible numbers circulate as "GDPval" (L4.D1) |
| D9 | number misleads | Set-substitution error | comparing a public/demo-set figure to a private/held-out figure | ARC-AGI-3 30.16% (25-env Public Demo) vs sub-1% (55-env Semi-Private) (L6.C18) |
| D10 | number misleads | Scaffold and subset drift between reporters | comparing a vendor's internal-scaffold number to a maintainer's number under one benchmark name | Epoch attributed the o3 FrontierMath gap to scaffold, test-time compute, or a 180-vs-290-problem subset (L3.F12) |
| D16 | number misleads | Luck floor eats the signal | 4-option multiple choice at frontier difficulty | MMLU-Pro 4→10 options, 16–33pp drop (L2.C15) |
| D17 | number misleads | Prompt-format variance reported as capability | single-prompt scoring | MMLU-Pro measures across 24 prompt styles and publishes the residual 2% (L2.FA-14) |
| E1 | baseline and humans | No human baseline, so saturation is invisible | shipping without a human number | TheAgentCompany and AndroidWorld have none (L5.F12); BALROG, FLE, TextArena, lmgame-Bench and Game Arena have none (L6 gaps) |
| E2 | baseline and humans | Human baseline by assertion | quoting a human number gathered under different information conditions than the model's | ARC-AGI-3's counter: identical system prompt, first-run-only, median-not-best reference (L2.FA-7) |
| E3 | baseline and humans | Unblinded panel | telling human testers they are calibrating an AI benchmark | ARC's counter: no mention of ARC Prize or AI testing at any point (L2.C5) |
| E4 | baseline and humans | Decaying human baseline | eliciting once and comparing forever | ForecastBench's superforecasters answered a July-2024 set; the 2026 parity claim is an extrapolation the maintainers discount (L4.C7) |
| E5 | baseline and humans | Ceiling mistaken for capability | advertising a human baseline that models "beat" when it was non-expert or unincentivized | L8 atlas #4; OSWorld's 72.36% now exceeded at 83.5% (L5.C10) |
| E6 | baseline and humans | Experts stop adding value | assuming the expert baseline stays above the frontier | physicians improved Sep-2024 references 56.2% vs worsened 39.8%; for Apr-2025 references, 46.8% vs 47.7% (L7.C24) |
| F-a | lifecycle | Born dead | no launch-score target and no frontier-baseline pass before publication | L8 atlas #1; the norm in `## The launch-headroom norm` |
| F-b | lifecycle | Saturation without replacement | freezing a set and letting the frontier walk into the ceiling | Terminal-Bench 2.0 gained ~20 points in ~4 months (L1.C13) |
| F-c | lifecycle | Repair-to-death | fixing every broken task without re-checking that headroom survived | "no task is unsolved in 2.1" (L1.C10); see **F13** |
| F-d | lifecycle | Zombie benchmark | no Retirement lifecycle stage and no retirement statement in official artefacts | BetterBench's recommendation (L8.C13) |
| F-e | lifecycle | Successor inherits the defect | replacing a contaminated benchmark with one built the same way | SWE-bench Pro shipped the git-leak channel and a 32.4% verifier-disagreement rate (L1 atlas #11) |
| F-f | lifecycle | Filter-induced selection bias | selecting items by one solve criterion and scoring them under another | Apex's pass@4-select / pass@k-score mismatch (L3.C15) |
| F-g | lifecycle | Sponsor holds the answer key | the party whose scores are reported holds the problems *and* the solutions | FrontierMath/OpenAI (L3.C2, L2.C14) |
| F-h | lifecycle | Contributor consent gap | recruiting item authors without disclosing funder identity and data access | named by the maintainer as its own failure (L3.F4) |
| F-i | lifecycle | Unenforceable non-training term | relying on a verbal agreement instead of a technical holdout | the holdout is the only control checkable from outside (L3.C6) |
| F-j | lifecycle | Best-of-N disclosure bias | no pre-registration of the evaluated variant | 27 private variants in one release cycle; up to 112% relative gain from arena-data access (L8.C20) |
| F-k | lifecycle | Unaudited self-report | accepting scores without trajectories | Terminal-Bench 2.1 responded by requiring public trajectories; SWE-bench by requiring trajectories plus author provenance (L1.C14) |
| F-l | lifecycle | Self-selected graders for prestige claims | the claimant chooses the graders | two identical 35/42 IMO claims, one IMO-certified and one graded by medalists the claimant engaged (L3.F13) |
| F-m | lifecycle | Environment rot | allowing network access or unpinned base images | 9 Terminal-Bench tasks; ~10% of OSWorld tasks read live internet data (L1.C9, L5.C8) |
| F-n | lifecycle | Resource-budget flake | a timeout or memory budget a valid solution can exceed on some hosts | 8 Terminal-Bench 2.0 tasks; produces variance uncorrelated with capability (L1 atlas #6) |
| F-o | lifecycle | Drifting measuring stick | ranking against a live open pool with no fixed anchors | TextArena TrueSkill, Game Arena all-play-all; countered by permanently-active organizer baselines (L6 atlas #1) |
| F-p | lifecycle | Intransitivity collapse | fitting a scalar skill to a game with non-transitive structure | Game Arena's maintainers replaced Elo with equilibrium rating for Werewolf (L6.C5) |
| F-q | lifecycle | Benchmark monoculture | choosing benchmarks by prestige with no coverage taxonomy | top ~22% of NLP datasets account for half of all use (L8.S5) |

## Recommendation register

Rank-ordered, highest value first. Every row names the benchmaker
artifact it changes, the failure it prevents, its evidence ids, its cost
(A7) and its adversarial verdict (A9) — and its **distinct-witness
count**, because several rows cite four or five evidence ids that resolve
to one upstream. Witness count, not id count.

**A8** — QC-1..QC-10 gate validity and none gates difficulty, so a
benchmark its target scores 100% on qualifies cleanly today — is closed
by **RF-01** and **RF-18** jointly. Neither blocks qualification; both
convert an invisible gap into a recorded one.

*A9 note — authorship, stated plainly.* Verdicts on **RF-01..RF-17** were
rendered by run item **C1** (`orch-critique`), a context that authored no
part of the synthesis; they are reproduced verbatim in `## Adversarial
verdicts` and this gate softened none of them. Verdicts on
**RF-18..RF-21** were rendered by **this gate, which also authored those
four rows** — author and verdict are the same context, so those four are
self-assessment, not adversarial review, and are weaker evidence than
C1's disjoint pass. They are marked `GATE-AUTHORED`, each carries the
weakness the gate found against its own row, and sending them to a
disjoint context is the first thing a successor run owes A9.

Artifact keys: **PROT** `compositions/references/benchmaker-protocol.md`
· **EVD** `skills/workflows/orch-eval-design/SKILL.md` · **QC**
`benchmarks/benchmaker/qualification/index.md` (+ the owning law in PROT
§Qualification) · **MAN**
`compositions/references/benchmaker-manifest.md` · **RCH**
`compositions/references/benchmaker-research.md`.

| id | recommendation | artifact changed | failure prevented | evidence | witnesses | cost | verdict | rank |
|---|---|---|---|---|---|---|---|---|
| **RF-01** | Add **QC-11 pre-seal headroom measurement**, *non-blocking*: before sealing, run the target's current incumbent against the **candidate-accessible portion** of the assembled set and record the score, the measured scope, the incumbent identity and the date. Publish that score in the manifest beside the field's published band (0.1–9%, L8.C9; ≥5% meaningfulness floor, L8.C10) as **two recorded figures with a declared gap** — not as a pass/fail threshold. Where the score sits above the band, the record must state which of the two **X13** readings applies: **saturation** (the set is too easy; the repair is difficulty) or an **over-lenient oracle** (the repair is the oracle, via RF-05 and RF-04). The two demand opposite repairs and must never share one verdict. | QC + PROT §Qualification + MAN | **F-a born dead / F-b saturation without replacement**, and the X13 conflation. Today a benchmark its target scores 100% on passes all ten required criteria and seals with a recomputable identity — and nothing distinguishes that from a benchmark whose oracle is too lenient. | L8.C9, L8.C10, L1.C13, L3.C14, L5.C10, X13 (L5.C8/C10/C14), G12 | **2** for the band — Press's blog and ARC's own leaderboard policy, both maintainer self-reports about their own artifacts, measuring different constructs; **3** disjoint for the decay it catches (Terminal-Bench, MathArena Apex, OSWorld). Two witnesses cannot carry a gate, which is why the band is published as retrieved figures rather than adopted as law. | one qualification run on the candidate-accessible scope; recording only — no pass/fail branch, therefore no revision loop and no successor-per-failed-attempt chain. The manifest fields are a supersession PR. | C1 **OVERREACH** — applied: band demoted to a recorded figure, X13 split out, measurement scope bounded (PROT §Materialization bars exposing protected evidence to a candidate context) | 1 |
| **RF-18** | Require every sealed case to declare an **anchor outside the package**: the reference its expected outcome is bound to — a human reference trace or time, a declared cost, or a world outcome that resolves independently — or to record `ANCHOR: none` with the reason. An anchored expectation is a headroom floor that needs no imported leaderboard band: the case stops being hard or easy relative to its author and becomes hard or easy relative to something the candidate cannot move. | PROT §Materialization + MAN (per-case field) | **E1 no human baseline, so saturation is invisible**, and F5's stated consequence: benchmaker's cases are scored against authored expectations only; nothing in the current set is anchored to a human, a cost, or a world outcome. | F5: L2.C3 (RHAE human action trace), L5.C19 (RE-Bench human time curve), L1.S19 + L4.C9 (real money), L4.C5 (world resolution), L6.C6 (frozen reference opponent), L5.S24 + L6.S16 (live human competitors) | **5** disjoint upstreams across five blind lanes — F5's own count, no shared upstream | one declaration per case; `ANCHOR: none` is legal and free, so the cost is the honesty of the record, not new measurement | **GATE-AUTHORED — SOUND.** C1 named this the largest omission in the register and the honest alternative to RF-01. **Weakness the gate records against its own row:** an anchor is cheap to declare and hard to make binding, and none of the five witnesses *mandates* one — each built one. This row states as law something the field only practises. | 2 |
| **RF-05** | Require a **reference-correctness audit** by a third context, disjoint from both the builders and the first qualifier, over every case's expected outcome — not the probe, the *expectation*. Record the defect **count** and its taxonomy class (not a rate: at n=16 a rate has 6.25pp granularity and no usable interval) plus a re-grade path in the manifest. Probe inversion (QC-2) proves the probe can fail; nothing currently proves the expected outcome is the right one. | QC + PROT §Qualification | **F1 silent reference-answer errors / F2 manufactured headroom.** The field's measured prior for hand-authored expert items is 10%–46%. | F1: L1.C3, L2.C8, L3.C8, L5.C5, L5.C8, L8.C22; L2.S22 supplies the reusable error taxonomy | **6** — UTBoost (L1.S16), HLE-Verified (L2.S16), Epoch/FrontierMath (L3.S3), SABER (L5.S8), Epoch/OSWorld (L5.S12), FutureHouse (L2.S15 = L8.S18, one shared upstream between L2 and L8, discounted to one) | one audit lane per successor; a third disjointness class is the largest recurring context cost any row adds; the taxonomy is reusable across successors | C1 **SOUND** — applied: defect *rate* replaced by count plus taxonomy class | 3 |
| **RF-04** | Make an **adversarial oracle-attack audit** a required pre-seal step, run against the published eight-class taxonomy (isolation failure, answers shipped with test, remote code execution, judge prompt injection, weak string matching, evaluation-logic gaps, trusting untrusted output, excessive permissions), and use it as the candidate-inaccessible check that currently leaves optimization resistance UNVERIFIED. Name the taxonomy a **dated opening checklist**, not permanent law — it is one 2026 paper, and freezing it freezes a 2026 attack surface. | QC (QC-9 extension) + PROT §Qualification | **F3** — the container, the harness and the scorer are attack surfaces independent of the task (atlas B3 for the environment-attack case). Benchmaker's probes execute in the same tree as the package they grade, and the protocol records optimization resistance UNVERIFIED for want of exactly this check. | L5.C14, L5.C15, L5.C16, L1.C5/C6, L6.C10, L8.C21 | **5** — BenchJack (L5.S29: L5.C14 and L5.C15 are the *same* source id, counted once), METR (L5.S26), the SWE-bench / SWE-bench Pro git-leak issues (L1.S12, L1.S13), Palisade (L6.S24), OpenAI CoT-monitoring (L8.S28) | one adversarial qualification lane per successor, reusing `orch-critique`; **unpriced and named as such**: no repair bound when the audit fails, and the auditing context needs precisely the access the audit exists to deny | C1 **SOUND** — applied: taxonomy dated; BenchJack counted as one witness, not two | 4 |
| **RF-03** | Add **QC-12 live-target discrimination**, *reporting-only*: the sealed set is run across at least two real candidate rungs (two model tiers, or two effort levels of one model) and the observed separation is recorded with its interval. Recorded, not gated — the cited evidence supports *reporting* separability and no retrieved source supplies a threshold, and an unthresholded "non-degenerate" gate is satisfiable by rerun noise. | QC + PROT §Qualification | **Silent saturation.** The current discrimination law proves the set fails seeds the qualifier wrote; it never proves the set separates systems anyone would actually campaign. | L6.C12, L8.C13, L2.C20, L7.C14 | **4** distinct (lmgame L6.S10; the retirement trio inside L8.C13; ARC L2.S2; Arena-Hard L7.S3/S4) — **and none of the four gates on separability; all four report it** | two candidate runs per qualification; supersession PR | C1 **OVERREACH** — applied: gate demoted to a recorded separation, the missing threshold named rather than invented | 5 |
| **RF-19** | Run the same sealed cases under **two oracles of different kinds** — the observable-outcome probe, and a trace-level check of the path that produced it — and **report the pair, never sum it**. The gap between them is the direct test for **C6** (a state oracle passing a candidate that skipped the work), which no other row covers, and it reuses the case set rather than adding one. | PROT §Qualification (a second recorded verdict per case) + MAN (scoring reports the pair) | **C6 state oracle passes a candidate that skipped the work**, and F12's answer-only overstatement. Benchmaker's probes inspect package bytes and outputs, never the path — **X2** records this as live and unresolved. | F12: L3.C12, L1.C3; the designs that ship the contrast: L4.S13 (FinQA execution *and* program accuracy), L3.S17 (CritPt oracle-answer injection), L5.S28 (BFCL requires both checks) | **5** distinct (MathArena/USAMO L3.S12; UTBoost L1.S16; FinQA L4.S13; CritPt L3.S17; BFCL L5.S28) — but F12's *own* contrast is one lane with one corroborating lane, so the core claim carries **2**, and the other three are implementations of the pattern, not independent tests of it | one extra recorded verdict per case at qualification; no new cases | **GATE-AUTHORED — SOUND with a bounded scope.** **Weaknesses the gate records against its own row:** F12 is L3 corroborated by L1, not five-lane convergence; and a trace oracle re-imports exactly the correct-but-different failure benchmaker's equivalence bridge (W4) excludes from scoring. Reporting the pair is defensible; **scoring on the trace is not**, and this row must never be read as licensing it. | 6 |
| **RF-20** | Replace the campaign's **net-sum score** with an aggregation that cannot be bought with easy cases: report the per-criterion vector and aggregate by harmonic or geometric mean, or an explicit level weighting. An arithmetic net sum over heterogeneous criteria is a headroom leak — one saturated criterion pays for one that still discriminates. | MAN (scoring law) + PROT §Scoring | **F19 composite averaging.** Benchmaker's score is a net sum (`net 27/32`); a candidate that wins the easy criteria and fails the discriminating one scores like a candidate that does the reverse. | F19: L2.C16 (BBEH harmonic mean), L6.C8 (Crafter geometric mean over 22 achievements; ARC-AGI-3's 5/15 level weighting), L4 atlas #16 (FinBen), L6 atlas #6 (BALROG's saturated Crafter) | **5** distinct across three blind lanes with no shared upstream (F19's own label): BBEH L2.S19, Crafter L6.S17, ARC-AGI-3 L6.S2, FinBen L4.S14, BALROG L6.S6 | arithmetic over existing trial data; one scoring-law sentence and one manifest field — the cheapest row in the register | **GATE-AUTHORED — SOUND.** **Weaknesses the gate records against its own row:** at 16 cases a geometric or harmonic mean is dominated by the single worst criterion, which at this size can be one case, so the per-criterion vector must be reported *beside* the aggregate, never replaced by it; and the row collides head-on with **X5** (Press's one-number rule against HELM's many-metric rule), which this register does not resolve — RF-21 declares the tiebreak instead. | 7 |
| **RF-08** | Make cost a **reported axis, not only a bound**: the candidate result identity carries observed per-case cost and the campaign reports `(score, cost)` pairs. QC-8 already bounds cost; nothing publishes it beside the score. The pair carries the host, the price list and the date it was observed, and **RF-16's cross-identity incomparability declaration owns the cost axis too** — a cost figure does not cross a price-list boundary any more than a score crosses an identity boundary. | MAN + PROT + QC-8 scope | **Cost-blind saturation / brute-force capture.** Without it, a higher score bought with more spend is indistinguishable from a better candidate. | F15: L2.C12, L1.S6, L4.C16, L3.S9, L7.C7 | **5** — ARC's three arcprize.org pages inside L2.C12 count as **one**; Aider (L1.S6); Vals AI (L4.S10, abstract-only, full-text fetch failed); MathArena (L3.S9); PaperBench (L7.S8) | recording only; the runner already measures wall time for QC-8 | C1 **SOUND** — applied: the cost-decay problem C1 raised is assigned an owner (RF-16) rather than left between two rows | 8 |
| **RF-14** | Bind the **candidate's harness** into the result identity — model id, effort level, host binding, and any scaffold — because a score is a property of (candidate × harness × benchmark) and benchmaker currently pins only two of the three. **Priced:** together with RF-16, every model version, effort level or host change mints a fresh result class, so a campaign spanning a model upgrade yields two histories, and the bridge is a re-run of the retained candidates, not an annotation. | MAN (result identity) + PROT | **F21 scaffold confounding / D10 scaffold and subset drift between reporters.** | L6.C12, L6.C13, L1.S3, L3.C9 | **3** distinct (lmgame L6.S10; Terminal-Bench L1.S3; Epoch L3.C9). L6.C13 is a relayed maintainer quote (L6.S19, `primary=no`) and is **not** counted. | recording only; `drift-canary` already tracks these bindings. The comparability cost is priced in the row rather than left to RF-16. | C1 **SOUND** — applied: the unpriced comparability cost named | 9 |
| **RF-16** | Declare **cross-identity incomparability** in the manifest: campaign scores do not cross a benchmark-identity boundary without an annotated regrade. **Priced:** an improvement claim spanning a supersession requires re-running every retained prior candidate against the successor; "annotated regrade" is the *name* of that re-run, not a substitute for it, and without it the campaign history is uncitable at the boundary. | MAN + PROT §Manifest | **F14 versions silently mix.** The field learned this after leaderboards were already polluted. | L5.C6, L5.C10, L8 atlas #24 | **2** distinct (Sierra τ³ L5.S4; OSWorld L5.S13/S14); L8 atlas #24 is a lane synthesis of the same shape across refresh benchmarks, not a third witness | one manifest field plus one law sentence — **plus** the re-run the escape hatch actually costs | C1 **SOUND** — applied: the regrade cost priced | 10 |
| **RF-21** | State an **arbitration order** for the three-way pressure this register creates — minimality pushes set size down, resolution pushes it up, headroom pushes difficulty up. The order: (1) **validity first** — no case is added or removed to move a score; (2) **coverage second** — the declared coverage floor (RF-02) is not tradable; (3) **resolution third** — where size and resolution conflict, declare the resolution and report it; do not buy cases toward a power target; (4) **headroom is recorded, never bought** — RF-01 and RF-03 produce figures, not gates, so headroom never wins an argument against validity. **X5** resolves the same way: report the vector, aggregate for the headline (RF-20), and never let the headline's shape select cases. | PROT §Qualification + EVD (stated once, in one place) | **The register's own incoherence.** Without an order, RF-01, RF-02 and RF-07 are three simultaneous demands on size and difficulty with no tiebreak, and the tie gets broken by whoever writes the ticket. | X5 (L8.S4 vs L8.S17), X6 (L8.S4's 500 cap vs L8.C16's ~969), and the RF-01 / RF-02 / RF-07 conflict C1 named | **2** field witnesses (Press L8.S4; HELM L8.S17 and Miller L8.S22 on the other side) — and they are the two sides of an *unresolved* disagreement, not support for this ordering | one ordering sentence in two artifacts; no measurement | **GATE-AUTHORED — SOUND as a coherence repair, UNSUPPORTED as a field claim.** No retrieved source states this ordering. X5 and X6 are recorded **unresolved** and this row does not resolve them: it declares which way benchmaker breaks the tie. That is a policy, and the row says so rather than dressing it as a finding. | 11 |
| **RF-02** | Leave EVD's minimality directive **candidate-blind** and bound it from below instead: the design declares, per case, the smallest deviation the case is built to discriminate, and minimality may not reduce the set below that declaration. The headroom check stays at qualification (RF-01), where candidate contact is licensed. **Premise repaired:** the row previously amended EVD with "*and that clears the declared headroom band*" — a clause checkable only by reading a candidate score, inside the one skill contractually barred from it ("inspect no candidate, variant, score, or winner identity"; "Never: … revise the design from scores"). | EVD (declaration only) + QC / PROT §Qualification (the score-facing half) | **F-a**, by the specific benchmaker path: a design that satisfies minimality and coverage while every case is trivially passed. | L8.C16 (power pushes size *up*), L8.D3 (the 500-cap vs 969-power conflict), F16 | **2** (Press L8.S4; Miller L8.S22) — **and both speak to set *size*, not headroom.** No retrieved witness supports a headroom clause at design time; that is why the score-facing half moved to qualification. | one declared field per case at design time; one sentence in EVD; no benchmark identity change | C1 **OVERREACH** — applied: the score-reading clause removed from EVD entirely, the blindness invariant restored, the check relocated | 12 |
| **RF-06** | Keep the **reporting law** and drop the QC-7 extension: **no delta smaller than the measured rerun spread is reportable**, and the spread is recorded in scoring and in the manifest. PROT already requires that for a nondeterministic outcome good variants pass and bad variants fail on **every** declared trial — strictly stronger than an SD band — so QC-7 needs no extension. **Recorded weakness:** at QC-7's k=3 an SD carries two degrees of freedom, so report the observed spread (max−min), not an SD, until a trial count supports one. | MAN + PROT (scoring law only) | **F16 rerun drift / F9 grader-noise ceiling.** A 23-run audit found an 18.9pp spread on identical reruns — wider than most gaps anyone reports. | L7.C16, L7.C17, L5.C21, L8.C14, L8.C15 | **5** ids, **1** carrying the headline 18.9pp figure (L7.S26 — a *different domain*, tool-calling, read from a search extract, cited only for magnitude). **G6 records that rerun variance has never been measured on a judged benchmark**, so the premise is unmeasured for the case class the row targets. | k× execution for nondeterministic cases only; QC-8's cost bound absorbs it if k is declared | C1 **OVERREACH** — applied: QC-7 extension dropped as redundant, reporting law kept, SD replaced by observed spread at k=3 | 13 |
| **RF-09** | Record **perturbation-generated seeding** in RCH as a sanctioned craft pattern: derive bad seeds by programmatically perturbing a proven-good reference at a declared deviation magnitude, so the deviation is known by construction. **Premise repaired — no law change is needed.** PROT constrains seed *provenance* ("variants supplied by the qualifying context"), never authoring mode, and the one-inert/one-near-miss mandate lives in `evaluation-design.md`, a sealed benchmark artifact, not in PROT §Materialization as the row previously claimed; perturbation seeds are already lawful. Two constraints carry: the **generator must be owned by the qualifying context**, or the qualifier's seeds become builder-authored and the disjointness qualification rests on breaks; and at 16 cases the generator buys a **tunable deviation magnitude, not contamination resistance**. | RCH (craft pattern) — **not** PROT | **Seed-authoring cost as the ceiling on set size**, and the burn-law getting harder each round. **The A3 claim is withdrawn:** L6.C4 puts the generator-versus-fixed-key threshold near 10⁴ instances, and is itself search-summary-only. | F6: L4.C17, L3.C19, L2.C18, L5.C23, L6.C4 (**and its bound**) | **5** fully disjoint (FinVerBench L4.S17; Putnam-AXIOM L3.S16; ZebraLogic L2.S21; AndroidWorld L5.S23; Procgen L6.S18 — the last search-summary-only and flagged for re-verification before load-bearing use) | one generator script per case family, owned by the qualifying context; amortizes across successors. No supersession PR — RCH is not a covered byte. | C1 **OVERREACH** — applied: the false premise about PROT removed, artifact moved from PROT to RCH, the A3 claim withdrawn, generator ownership named | 14 |
| **RF-10** | Declare a **retirement trigger** at seal time in the manifest — the condition under which this identity stops being citable (incumbent at or above RF-01's recorded band, or candidates indistinguishable at RF-06's measured spread). **Repaired:** the *firing* is recorded **outside the sealed scope**, which `SEALS.md` leaves open only for `benchmark.lock`, `SEALS.md` and `FINDINGS-*.md`; recording it in the manifest changes a covered byte and mints a successor, so a benchmark could never be marked retired without ceasing to be that benchmark. | MAN (the declaration) + a consumer-side record outside the sealed scope (the firing) | **F-d zombie benchmark.** Benchmarks are immutable here; nothing says when one stops being *informative*. | L8.C13, L1.C15, L3.S14, L8.S25 | **3** on the recommendation (ARC-AGI-2, BetterBench, the 60-benchmark study, all inside L8.C13) and **0** on any numeric threshold — L8.G10 records that all three specify nothing beyond "statistically indistinguishable". L1.C15's third leg is secondary trade reporting the lane marks not claim-grade and is not counted. | one manifest field, one non-covered record; supersession PR for the field only | C1 **OVERREACH** — applied: the firing relocated off the covered surface; the numeric trigger declared as benchmaker's own policy, not a field norm | 15 |
| **RF-12** | **Certify the judged oracle before sealing it**: hand-label a fixed example set, measure every candidate judge against it, pin the winner by identity, and publish the agreement table beside the score. QC-7 records that the judge is *stable*; nothing records that it is *right*. **Ranked here on purpose:** G1 records that the field's most mature judge-certification literature (WMT/MQM) was **not searched** and bears directly on this row, and a row should not be ranked on evidence the report says it did not gather. At benchmaker's scale — one judged case, and judged criteria that cannot compensate for a required deterministic failure — a mis-certified judge cannot flip a verdict, so this row waits on the G1 follow-up. | QC (QC-7 extension) + MAN | **C8 proxy-oracle inversion / F9 aggregate-agreement concealment.** Stability without accuracy is what a consistently wrong judge looks like. | L7.C7, L7.C4, L7.C2, L4.C4 | **5** — JailbreakBench (L7.S20; L7.S21 is the same paper in a second rendering, counted once), PaperBench (L7.S8), StrongREJECT (L7.S10), HealthBench (L7.S7), GDPval-AA (L4.S3) | one labelling pass over the single judged case; the hand-labelled set is itself a new unqualified artifact needing its own provenance story | C1 **OVERREACH** — applied: ranked down and made explicitly conditional on the G1 follow-up | 16 |
| **RF-07** | Declare the set's **smallest reportable difference** in the manifest, derived from **measured rerun spread** (RF-06), and state it beside every campaign result. **Premise repaired:** L8's packet labels the 969-question figure "worked under stated fictional parameters and does not transfer unchanged", and sampling power presumes items drawn from a population one means to generalize to — benchmaker's cases are a purposive census of declared coverage, so there is no super-population and a sampling-derived figure answers a question the set does not ask. Publishing a power-derived figure also invites the wrong repair: buying cases toward 969, which no bound carries. | MAN + PROT | **F16 under-powered eval.** The incumbent's net 27/32 has an interval nobody has published; most plausible candidate deltas are unreadable inside it. | L7.C17 (measured rerun spread), L8.C15 / L8.C16 (**recorded as non-transferring, not relied on**), L8.D3 | **1** usable (the rerun-spread measurement, L7.S26, different domain); the two power figures collapse to **1** (Miller L8.S22) and are recorded as a non-transfer | arithmetic over existing trial data; no new runs | C1 **OVERREACH** — applied: derivation switched from sampling power to measured rerun spread; the 969 figure demoted to a recorded non-transfer | 17 |
| **RF-13** | Report **pass^k** (all k trials succeed) beside pass@1 in **campaign results**, using the definition in words and **no cited estimator** — G4 records that two lanes independently failed to retrieve a primary formalization. Drop the qualification half as redundant: PROT already requires good variants to pass and bad variants to fail on *every* declared trial, which is pass^k at that layer. **Recorded weakness:** at k=3 pass^k is near-binary and will read as a capability difference when it is a coin flip; and without a retrieved estimator each campaign risks defining the metric locally, which is **D8 metric drift**, catalogued here as a failure. | MAN + scoring law | **F16 run-selection inflation.** A pass@1 headline describes a system that may fail the same case most of the time. | L5.C2 | **1** (Sierra L5.S2) | reuses the trial count QC-2 already declares | C1 **OVERREACH** — applied: qualification half dropped, estimator claim withdrawn, k=3 weakness recorded | 18 |

### Declared non-opportunities

Three rows were withdrawn at the gate on C1's verdicts. C1's full
reasoning is in the verdict rows below; what a successor must not lose is
recorded here, because a withdrawn recommendation that leaves no record
is re-proposed by the next run.

**RF-11 — build N+k cases and seal N, holding k as the successor's refill
set. WITHDRAWN (C1: WRONG).** It deepens the **F-e successor-inherits-the-
defect** failure it claims to prevent — k cases authored in the same
sitting, by the same builders, from the same frozen evidence are the
maximally inherited successor, the case the burn-law was written against —
and its cited mechanism (L2.C11, two CAIS-controlled ids resolving to
**one witness**) swaps items *inside a live set*, which immutability
forbids. The reservoir cases would never have crossed QC-1..QC-10.
**Queued, not fixed:** C1 notes the F-b half, a refill path against
saturation, is a real if smaller gain that could stand as its own row; it
is not written here because it would be a new recommendation with no
verdict.

**RF-15 — re-classify harness-attributable probe crash loci as UNVERIFIED.
WITHDRAWN (C1: UNSUPPORTED).** Its sole evidence (L3.C23) is PROVISIONAL,
unrendered, and about a different system, which this run's source policy
makes a recorded gap rather than claim-grade support; and the law already
exists (W3). The read remains prudent as a **ticket against the current
benchmark**, not a change to law — acting on it changes probe bytes and
mints a successor, which the withdrawn row never priced.

**RF-17 — fix a parameterized difficulty dial at the smallest value at
which the incumbent fails. WITHDRAWN (C1: WRONG).** It is *revising the
design from scores*, named under **Never** in `orch-eval-design`, and it
calibrates difficulty to the system under test — which this report's own
**F20** and **G9** record as a convergent *empty* result and an explicit
non-opportunity, incompatible with a sealed case set. L2.C18 and L4.C17
show dials are fixed **in advance**; neither supports tuning one to the
target. It also contradicts RF-01: a case tuned to incumbent-failure
scores zero by construction, at its maximum-variance threshold.


## Adversarial verdicts

Rendered by run item **C1** (`orch-critique`), a context that authored no
part of this report and read the eight lane packets, the frozen spec and
benchmaker's current bytes directly. **Closes A9.** Verdicts are on the
recommendations *as written*; repairs belong to the gate, not to this
pass.

Classes: **SOUND** — the evidence supports it, it lands on a real
artifact, and it would prevent the failure it names. **OVERREACH** —
directionally right, but claims more than the evidence carries or costs
more than it returns. **UNSUPPORTED** — the cited evidence does not
establish the premise. **WRONG** — it would not prevent the named
failure, or it causes a worse one.

Tally: **5 SOUND · 9 OVERREACH · 1 UNSUPPORTED · 2 WRONG.**

| id | verdict | reasoning | what breaks if adopted |
|---|---|---|---|
| **RF-01** | **OVERREACH** | The gap is real and recording the incumbent's pre-seal score closes it. The *band* is not a field norm: L8.C9 is one maintainer's blog, which L8's own packet labels "not a standard" asserting "no evidence base"; L8.C10 is ARC's self-declared policy for its own public leaderboard. Neither is corroborated, they measure different constructs, and the "5%–9%" composite is authored in this report, not retrieved. A hard FAIL also collapses the report's own X13 — a high incumbent score is not distinguishable from an over-lenient oracle — into one verdict, though the two demand opposite repairs. | On a 32-point instrument the band admits exactly one attainable integer score (2/32 = 6.25%), so as stated it is near-unsatisfiable. A FAIL forces set revision after qualification has fixed an identity, minting a successor per failed attempt with no bound on the loop. And running the incumbent against the *assembled* set either exposes protected evidence to a candidate context — barred by PROT §Materialization — or measures headroom on the public half only, exactly where contamination is worst. Keep the measurement and publish the band in the manifest as a **recorded figure with a declared gap**, benchmaker's own idiom for this; do not make it blocking. |
| **RF-02** | **OVERREACH** | It amends the one skill that is contractually candidate-blind — "inspect no candidate, variant, score, or winner identity", and "Never: … revise the design from scores" — with a clause the designer can only check by reading a candidate score. Its cited support (L8.C16, L8.D3) argues for a **size** floor, a different quantity from headroom. Without RF-01 there is no band to clear. | Either the clause is unverifiable at design time and changes nothing, or it breaks eval-design's blindness invariant and lets candidate performance select cases. The check belongs at qualification, where candidate contact is already licensed. |
| **RF-03** | **OVERREACH** | A genuine change — today's discrimination law proves only that the set separates seeds the qualifier wrote. But the cited evidence supports *reporting* separability, not gating on it: L7.C14 is an Arena-Hard paper claim, L6.C12 is single-source and about a harness rather than a case set, L2.C20 is ARC's own IID calibration. "Non-degenerate" carries no threshold. | Satisfiable by rerun noise: two rungs differing by one case clear "non-degenerate" while sitting well inside the variance band RF-06 exists to name. Unthresholded, the criterion certifies noise as discrimination — and it can only be thresholded by RF-07, which is itself contested below. |
| **RF-04** | **SOUND** | Real change against a hole the protocol names itself: PROT §Qualification lets optimization resistance stand UNVERIFIED for want of exactly this check. The premise is four-lane convergent over disjoint upstreams — git leakage (L1.C5/C6), Palisade's default-hacking result (L6.C10), OpenAI's obfuscation finding (L8.C21) — not only the audit. | The eight-class taxonomy is one paper: L5.C14 and L5.C15 are the **same source id (S29)**, cited in the register as if two. Name it as a dated opening checklist or benchmaker freezes a 2026 attack surface as permanent law. Costs an unbounded adversarial lane per successor with no repair bound when it fails, and the auditing context needs precisely the access the audit exists to deny. |
| **RF-05** | **SOUND** | The best-evidenced row here: F1 is five lanes over six upstreams with only one shared. The gap is exact — QC-2 proves the probe *can* fail, QC-4 traces where an expectation came from, and nothing proves the expectation is right. | A third disjointness class (builders / first qualifier / auditor) is the largest recurring context cost any row adds. "Record a defect rate … exactly as an error budget" overstates what n=16 yields: the statistic has 6.25pp granularity and no usable interval. Record the defect **count** and its taxonomy class, not a rate. |
| **RF-06** | **OVERREACH** | The reporting law is sound and new. The QC-7 extension largely is not: PROT already requires that for a nondeterministic outcome "good variants pass and bad variants fail on **every** trial" at a declared trial count — strictly stronger than an SD band. Its headline number is labelled by L7 itself as a different domain (tool-calling), read from a search extract, "cited only for the magnitude of rerun variance". | G6 records that rerun variance has **never** been measured on a judged benchmark — the row's premise is unmeasured for the case class it targets. At the trial counts benchmaker declares (k=3 at QC-7), an SD carries two degrees of freedom and will suppress real deltas about as often as noise. |
| **RF-07** | **OVERREACH** | L8's packet labels the 969-question figure "worked under stated fictional parameters and does not transfer unchanged". More basically, sampling power presumes items drawn from a population you mean to generalize to; benchmaker's cases are a purposive census of declared coverage, so there is no super-population and a sampling-derived SDD answers a question the set does not ask. | Publishing a power-derived SDD invites the wrong repair — buying cases toward 969, which no bound carries and which X6 records as unresolved even in the field. Derive the resolution from measured rerun variance (RF-06) instead. As written, EVD minimality (size down), RF-07 (size up) and RF-01/RF-02 (difficulty up) form a three-way conflict the register never arbitrates. |
| **RF-08** | **SOUND** | Cheap, recording-only, and the gap is stated precisely: MAN carries `expected_cost` and QC-8 bounds it; nothing reports it beside the score. F15 is five lanes over five disjoint upstreams, and 54%@$30 against 24%@$0.20 is the register's clearest single demonstration. | Observed cost is a function of host, price list and date, none sealed by any identity, so a published `(score, cost)` pair silently decays and reintroduces the cross-boundary incomparability RF-16 exists to declare. Neither row says which owns that. (L4.C16, one leg, is abstract-only with a failed full-text fetch.) |
| **RF-09** | **OVERREACH** | The mechanism is well-evidenced across five disjoint upstreams, but the premise about current law is wrong: PROT constrains seed *provenance* ("supplied by the qualifying context"), never authoring mode, and the one-inert/one-near-miss mandate lives in `evaluation-design.md` — a sealed benchmark artifact — not in PROT §Materialization as the row claims. Perturbation-generated seeds appear already lawful; this is craft guidance, not a law change. | The named failure does not survive its own bound. L6.C4 — search-summary-only, and its packet says it "should be re-verified against the paper body before load-bearing use" — puts the generator-versus-fixed-key threshold near 10⁴ instances. At 16 cases the generator buys a tunable magnitude, not A3 resistance. And if builders own the generator, the qualifier's seeds become builder-authored, breaking the disjointness qualification rests on. |
| **RF-10** | **OVERREACH** | Declaring a trigger at seal time is cheap and right. Its numeric content is not evidenced: L8's G10 records that all three sources recommending retirement specify no threshold beyond "statistically indistinguishable", and the ceiling half inherits RF-01's contested band. L1.C15's third leg is secondary trade reporting the lane itself marks not claim-grade. | The trigger is declarable but not actionable: recording that it *fired* changes a covered manifest byte and mints a successor, so a benchmark can never be marked retired without ceasing to be that benchmark. The row needs a consumer-side register outside the manifest and does not name one. |
| **RF-11** | **WRONG** | The row names **F-e successor inherits the defect** among the failures it prevents, and the mechanism deepens it: k cases authored in the same sitting, by the same builders, from the same frozen evidence, are the maximally inherited successor — precisely the case the burn-law's fresh-in-name-and-locus rule was written against. Its cited mechanism (L2.C11, two CAIS-controlled ids = one witness) swaps items **inside a live set**, which benchmaker's immutability forbids; the transfer keeps the name and drops the property. | The reservoir cases are unqualified — they never crossed QC-1..QC-10 — so a successor either seals unqualified bytes or pays qualification twice. The F-b half is a real but smaller gain and stands on its own; it should be split out and the F-e claim withdrawn. |
| **RF-12** | **OVERREACH** | The distinction is exactly right — QC-7 proves the judge is stable, nothing proves it correct. But G1 records that the field's most mature judge-certification literature was **not searched** and "bears directly on RF-12"; a row should not be ranked on evidence the report says it did not gather. Of its cited ids, L7's S20 and S21 are the same paper in two renderings, and S21's figures came from a search extract. | Poor cost/return at this scale: one judged case, and W5's own law makes judged criteria secondary and unable to compensate for a required deterministic failure, so a mis-certified judge cannot flip a verdict. The hand-labelled example set is itself a new unqualified artifact needing its own provenance and disjointness story. |
| **RF-13** | **OVERREACH** | Redundant where it is strongest: PROT already requires good variants to pass and bad variants to fail on **every** declared trial, which is pass^k at the qualification layer. The campaign-reporting half is new but rests on one source (L5.C2) whose closed form the lane records as "not read directly" (L5.G1) and which L8 independently failed to retrieve (G4). | Without a retrieved estimator each campaign defines the metric locally — D8 metric drift, which this register catalogues as a failure. At k=3 pass^k is a near-binary statistic that will read as a capability difference when it is a coin flip. |
| **RF-14** | **SOUND** | A score is a property of (candidate × harness × benchmark); MAN pins the benchmark and emits a separate result identity but fixes no harness field. F21 is three lanes over disjoint upstreams, and Terminal-Bench's "submissions may not modify timeouts or resources" is the field enforcing the same rule. | Combined with RF-16, almost nothing stays comparable: every model version, effort level or host change mints a fresh result class, so a campaign spanning a model upgrade yields two histories with no bridge. That is correct, and it is a cost no row prices. (L6.C13 is a relayed maintainer quote, marked primary=no.) |
| **RF-15** | **UNSUPPORTED** | The premise is that some of the ~49 converted loci are harness-attributable; the report states outright this "is unestablished", and the sole cited evidence L3.C23 is **PROVISIONAL with zero rendered-primary backing** — search-engine renderings of a maintainer post about Gemini losing points to API errors on a different benchmark. Under this run's own source policy that is a recorded gap, not claim-grade support. The law it would add already exists: W3 says benchmaker's UNVERIFIED-on-crash path and QC-10 blocked-return shape **precede** the field's version. | Nothing breaks — the read is prudent — but it is a ticket against the current benchmark, not a change to law, and it is mis-filed as "QC + PROT (scoring law)". Acting on a re-classification changes probe bytes and mints a successor, which its cost cell does not price. |
| **RF-16** | **SOUND** | MAN says any covered byte change mints a successor; it never says what that does to prior scores, and the difference is behavioural — this report's own G12 compares net 27/32 on the retired 12-case set against a 16-case set at a different identity, the exact move the declaration forbids. τ³'s "not comparable" plus a retroactive re-grade is the field paying for the omission. | The "annotated regrade" escape hatch is the whole cost and the row does not price it: an improvement claim spanning a supersession requires re-running every prior candidate against the successor, or the campaign history becomes uncitable at the boundary. |
| **RF-17** | **WRONG** | Fixing the dial at "the smallest value at which the incumbent fails" is revising the design from candidate scores — named under **Never** in `orch-eval-design` — and it is calibrating difficulty to the system under test, which F20/G9 record as a convergent *empty* result the report itself calls "a recorded non-opportunity" incompatible with a sealed case set. L2.C18 and L4.C17 (each single-source, one abstract-only, one v1 preprint) establish that dials exist and are fixed **in advance**; neither supports tuning one to the target. | It contradicts RF-01 head-on: every parameterized case tuned to incumbent-failure scores zero by construction, driving the set below RF-01's own noise floor. It also parks every such case at its maximum-variance threshold — exactly where RF-06's rerun drift and RF-07's resolution problem bite hardest. |

### Report-level findings

**Economy — the length is not earned; roughly a fifth is recoverable.**
The `## Sources` block (238 lines) and the benchmark register (143) are
contract-bound by A1 and A3–A6 and should stay whole. Three blocks are
not. **(a) The failure atlas (101 lines) restates the findings it was
mined from**, entry by entry and on the same claim ids: C2 is F1,
B1/B2/B4/B6 are F3, D1/D2 are F9, D5/D6/D7 are F11 and F19,
D12/D13/D14 are F16. Keep the atlas as the taxonomy and cut the
findings' repeated evidence recitals to their consequence lines, or the
reverse — not both. **(b) `## What benchmaker already gets right` (99
lines) is mostly validation.** W1, W3, W7 and W9 earn their place
because each names a missing half that becomes a recommendation. W2,
W4, W5, W6, W8 and W10 change no behavior and name no owner; under this
repository's law that is framing, however well sourced — about 60 lines.
**(c) The launch-score table duplicates the register's `At release`
column** for 26 benchmarks carried again below; one of the two should be
a pointer. The disagreement register is A11-bound and stays, but X5,
X10, X18, X19 and X20 feed no recommendation and no gap and could
compress to their one-line statements.

**A cross-cutting defect the register inherits.** Convergence discounting
is applied rigorously at the finding level (F1..F22 name shared upstreams
and discount them) and not at all at the recommendation level. Several
rows list four or five evidence ids that resolve to one witness: RF-04's
L5.C14 and L5.C15 are one source id; RF-11's L2.C11 rests on two
CAIS-controlled surfaces; RF-08's L2.C12 is three arcprize.org pages;
RF-01's entire band is two single-source maintainer self-reports about
their own artifacts. An evidence column should carry witness count, not
id count.

**Missing — three findings that clearly support a recommendation and got
none.**

1. **F5's external anchor, the largest omission in the register.** F5 is
   five lanes over five disjoint upstreams and states the consequence
   flatly: "an anchor outside the system is what converts a score into a
   claim… nothing in the current set is anchored to a human, a cost, or
   a world outcome." Seventeen recommendations and not one proposes an
   anchor. RF-08 reports cost; it does not bind a score to anything
   outside the package. This is also the honest alternative to RF-01 —
   a declared reference outcome per case is a headroom floor that needs
   no imported leaderboard band.
2. **F12's dual-oracle contrast**, which the report itself calls "the
   highest-value diagnostic in the whole field" and "cheap, because it
   reuses the item set" — then omits. Running the same cases under the
   observable oracle and a trace oracle is the direct test for this
   report's own C6 (state oracle passes a candidate that skipped the
   work), which no recommendation covers.
3. **F19's aggregation law.** Three lanes converge that arithmetic
   aggregation over heterogeneous criteria is a headroom leak, and that
   harmonic, geometric and level-weighted aggregation cannot be bought
   with easy items. Benchmaker's score is a net sum (`net 27/32`). A
   scoring-law change is among the cheapest rows the register could have
   carried and it is absent.

Also absent: an **arbitration rule** for the three-way pressure the
register itself creates — minimality down, power up, headroom hard —
which X5 and X6 record as unresolved in the field and which the register
inherits without resolving.

### Gate disposition

One correction pass (`orch-review-fix`) applied C1's verdicts rather than
re-litigating them. Nothing above was softened: the verdict table and the
report-level findings are C1's own text, kept whole. Each surviving
register row carries its C1 verdict and the repair applied to it in its
`verdict` cell; three rows were withdrawn and sit in `### Declared
non-opportunities`; four were added and are marked `GATE-AUTHORED`.
**One C1 finding is only partly discharged.** C1 assessed roughly a fifth
of the report recoverable. The named cuts were taken — the launch-score
table, nineteen atlas rows restating F1/F2/F3/F9/F11/F16/F19, six
validation W-entries reduced to one line each, and X5/X10/X18/X19/X20
compressed — recovering 83 lines, which the repairs above then spent. The
balance of C1's estimate sits in atlas rows and W entries that carry a
claim or a source of their own, and the gate's bound forbids cutting
those. Compressing the findings' evidence recitals is the queued
alternative; it belongs to a successor run, not to a single correction
pass.

## What benchmaker already gets right

Where the field converged, expensively and after public damage, on
something benchmaker already does. **W1, W3, W7 and W9 each name a
missing half that became a recommendation and are stated in full; the
rest change no behavior and name no owner, so they are one line each.**

**W1 — Immutable identity with successor-on-change is the fix the field
retrofitted after polluting its leaderboards.** Sierra had to declare
"results produced with tau2-bench < 1.0.1 are not comparable with >=
1.0.1" and re-grade affected submissions *after* the fact (L5.C6);
OSWorld had to state that 2.0 and OSWorld-Verified are not interchangeable
(L5.C10); L8 records rolling-refresh incomparability as an unsolved
reporting problem with no anchor-item bridge in any retrieved source
(L8 atlas #24). Benchmaker mints a successor identity on any covered byte
change, by construction. **What is still missing** is the consequence:
nothing says prior campaign scores do not cross the boundary (RF-16).

- **W2 — qualification by a context disjoint from every builder** is the
  field's minimum bar and most of the field fails it: 14 of 24 assessed
  benchmarks report no significance or uncertainty, 17 of 24 ship no
  replication scripts (L8.C14); SWE-bench added author provenance only
  in 2025 (L1.C14); PaperBench and JailbreakBench are the two that built
  a labelled evaluation for their own judge (L7.C7).

**W3 — The blocked-return shape (QC-10) and the UNVERIFIED-on-crash
scoring path answer a failure the field is still making.** L3 records
harness loss scored as capability loss as a live defect: FrontierMath
forces submission at 660k of a 1M token cap and Gemini 3 Pro "lost points
on 10 questions due to API errors" (L3.C23). L5's independent answer is
the Evidence Pass / Evidence Fail / **Unknown** labelling with a reported
score *interval* quantifying the Unknowns (L5.C22). Benchmaker's
UNVERIFIED verdict is the same construct, and it precedes both. **Caveat:**
whether every one of the ~49 probe crash loci the 2026-08-07 supersession
converted to clean named FAILs is candidate-attributable rather than
harness-attributable is unestablished — carried as a ticket against the
current benchmark, not as a law change (see `### Declared
non-opportunities`, RF-15).

- **W4 — the equivalence bridge** (a bad variant counts only when shown
  to change the observable outcome; an equivalent variant is *excluded,
  not scored*) is stated as law nowhere in the field: τ² concedes its
  ACTION check "penalizes correct-but-different solutions" and leaves it
  out of the default reward basis (L5.C3), BFCL's mitigation is a *set*
  of minimal viable paths (L5.C17), Gaia2 needs causal and temporal
  constraints to make a trajectory oracle defensible (L5.C12).
- **W5 — deterministic oracles required, judged criteria secondary and
  unable to compensate for a required deterministic failure** is Press's
  rule ("avoid using an LM as both solver and evaluator", L8.S4) and
  LiveBench's design stance (L8.S11), stated as a protocol constraint
  rather than a preference.
- **W6 — the inert-variant mandate** is the probe-inversion test the
  field almost never runs; StrongREJECT's string matching at Spearman
  **−0.394** against human labels is an oracle anti-correlated with truth
  that nobody had inverted (L7.C4).

**W7 — Protected evidence off-tree, candidate-inaccessible by policy, is
the only contamination control the field endorses.** L8's canary
write-up concludes that any benchmark without a fully private eval suite
is at significant risk, having shown GPT-4-base reproducing the BIG-bench
GUID verbatim (L8.C5). Benchmaker already scopes its two-GUID canary as
**detection only**, which is exactly right — canaries provably fail as
prevention. **The gap** is that resistance is recorded UNVERIFIED for
want of a candidate-inaccessible check (RF-04).

- **W8 — the burn-law** (every seed deviation fresh in name and locus
  against the predecessor set) is the structural guard against
  successor-inherits-the-defect: SWE-bench Pro was built to replace
  Verified and shipped the git-leak channel plus a 32.4%
  verifier-disagreement rate (L1 atlas #11).

**W9 — Cost is declared and bounded (QC-8, `expected_cost`), which most
benchmarks do not do at all.** L4 found that of every benchmark
producing authored ground truth, **only FinQA and GDPval report both
cost and label stability** (L4.C22). **The gap** is that benchmaker's
cost is a bound, not a reported axis (RF-08).

- **W10 — claim-traced provenance (QC-4)** is the systematization step
  the construct-validity literature says is usually skipped: Wallach et
  al. find systematization "typically incomplete… often conflated with
  operationalization" (L8.S15) and Raji et al. make the same charge
  against GLUE and ImageNet (L8.S14).

## Disagreements

Recorded as found. No side is preferred, and none of these is resolved by
this report.

**X1 — HLE's current top score, between two maintainer boards.** L2
retrieved the Scale Labs maintainer leaderboard showing
`gemini-3.1-pro-preview (thinking high)` at **46.44 ± 1.96** (L2.S13).
L8 retrieved the agi.safe.ai maintainer site showing **Gemini 3 Pro
38.3%** (judge o3-mini, dataset finalized 2025-04-03) (L8.S12). Both were
fetched on 2026-08-08 and both are maintainer-run. Neither lane knew the
other had retrieved a different figure. Possible innocent explanations —
update lag, different judge, text-only vs multimodal subset,
with-tools vs no-tools configuration — are all unverified. Separately,
aggregator claims of Claude Fable 5 at 55.5% and Claude Opus 5 at 54.9%
appear in both lanes and are **UNVERIFIED and quarantined**; they enter no
register cell. **Unresolved. Load-bearing** because it means two
maintainer surfaces for the same benchmark disagree by 8 points.

**X2 — Is the trajectory part of the oracle?** *State only:* τ-bench
chose DB-state comparison precisely to be path-agnostic and to need no
human or LLM judgement (L5.C1), and τ²/τ³ ship an ACTION check but leave
it out of the default reward basis (L5.C3); WebArena scores functional
correctness of the outcome with intermediate actions unscored (L5.C13).
*Trajectory required:* Gaia2's ARE Verifier checks **every write action**
against oracle annotations with causal and temporal constraints (L5.C12);
BFCL v3 requires **both** checks on all turns, arguing each alone is
unsound (L5.C17). Both sides concede the other's failure mode. No source
runs a head-to-head on the same task set. **Unresolved** — and directly
live for benchmaker, whose probes inspect package bytes and outputs
rather than the path that produced them.

**X3 — Is partial credit legitimate?** *Yes:* OSWorld 2.0 argues binary
scoring "assigns the same score to an agent that makes no meaningful
progress and one that completes most subtasks but misses a final
verification step" (L5.C11); TheAgentCompany's 0.5/0.5 formula keeps
binary visible (L5.C18). *No, implicitly:* τ-bench, WebArena, GAIA and
BrowseComp all score binary, and the strongest empirical argument is
OSWorld 2.0's own table, where partial and binary produce **different
rankings**. Checkpoint weights are authored, so partial credit
re-imports the judgement that state oracles were adopted to remove. No
source quantifies how often the weights change the ranking.
**Unresolved.**

**X4 — What is the true defect rate of authored oracles?** Epoch says
~10% of OSWorld tasks and calls that typical (L5.C8). SABER finds 24 of
50 τ-bench airline tasks with identified errors and 31 of 50
under-specified (L5.C5). HLE-Verified finds 45.7% requiring revision
across all 2,500 items (L2.C8); FutureHouse finds 29.3 ± 3.7% on a
chemistry/biology subset and the HLE team's own follow-up ~18% on a
subset (L2.D2); FrontierMath v2 touched 42% (L3.C8); MMLU-Redux measures
6.49% overall (L2.C9). These do not measure the same population and the
headline rates differ by more than 7×. **Unresolved.** The direction is
unanimous, and L5's own reading — plan for the higher figure on
hand-authored items and the lower one on script-verified ones — is
recorded as a lane assessment, not a settled number.

**X5 — One number or many?** Press: have "**one number** for your
benchmark" (L8.S4). HELM: single-metric evaluation *is* the failure mode
— seven metrics per scenario "so that trade-offs are clearly exposed"
(L8.S17). Both primary, direct opposites, neither addressing the other.
**Unresolved.** Benchmaker sits on the one-number side (net N/M); RF-20
and RF-21 declare which way it breaks the tie rather than resolving it.

**X6 — How large must a benchmark be?** Press recommends 150 minimum,
300–500 target, "500 as an upper limit" (L8.S4). Miller's power analysis
puts ~**969 independent questions** behind an 80%-powered test of a
3-point difference (L8.C16). A 500-item cap and a 969-item power
requirement cannot both be satisfied; neither source cites the other.
**Unresolved, and acute for benchmaker at 16 cases / 32 points.**

**X7 — How much does contamination matter?** *Severe and hidden:*
paraphrase and translation bypass n-gram decontamination, and a 13B model
trained on rephrased test data reaches GPT-4-level on MMLU, GSM8k and
HumanEval (L8.C6). *Bounded and family-specific:* GSM1k measures drops of
only up to 8% and states "many models, especially those on the frontier,
show minimal signs of overfitting, and all models broadly demonstrate
generalization" (L8.C7). Both primary. **Unresolved.**

**X8 — Is adversarial model-failure filtering good design?** *For:* it is
HLE's stated construction (L2.C6), Apex bought a benchmark where the best
model scored 5.2% out of a corpus where models scored ~90% (L3.D4), and
Press endorses filtering out easy instances using strong baselines
(L8.D7). *Against:* it is the mechanism the label audit blames for wrong
gold answers (L8.C24, L2.FA-1), the filter biases the set toward whatever
the filter models happen to fail, and the headroom lasted ~9 months
(L3.C14). **Unresolved and consequential** — it is the join between the
headroom thread and the validity thread, and RF-01 and RF-05 are
deliberately paired because of it.

**X9 — Cheap judge or expensive expert?** GDPval's own data says an
automated grader agrees with humans at 65.7% where humans agree with each
other at 70.8%, and its authors call the 5-point deficit acceptable
(L4.D4); GDPval-AA v2 acts on that permission and grades a whole
leaderboard with an LLM judge, publishing no judge-validation figure
(L4.C4). FinanceBench and the legal audit go the other way and pay for
human review. Separately, L7 finds the distillation wins are all in
safety (short binary judgments — StrongREJECT's Gemma 2B at 0.900 beats
its own frontier rubric evaluator at 0.846) while the frontier wins are
all in long-form rubric grading (L7.D2). Whether distillation transfers
to long-form is untested in anything retrieved. **Unresolved.**

**X10 — Fixed rubric or per-instance generated criteria?** WritingBench's
dynamically generated criteria beat static baselines at 83% human
agreement (L7.C22); HealthBench and PaperBench spent enormous expert
labor on *fixed* criteria. **Unresolved in the literature**; for a sealed
benchmark the freeze side wins by construction — a construction
constraint, not an adjudication.

**X11 — Does recency solve contamination?** *For:* a measured 10–20
point (up to ~60 point) inflation on AIME 2024 vs 2025, with evaluation
run within hours of release (L3.D2). *Against:* near-duplicates of fresh
problems already exist online — the claim L3 could not verify at primary
(L3.G9) — and MathArena's own maintainers now say the whole final-answer
class is exhausted regardless of freshness. **Unresolved.**

**X12 — Is a realized-outcome oracle the honest one or the misleading
one?** Prediction Arena argues real-money settlement "cannot be gamed or
overfitted" (L4.D3); the alpha critique names six ways realized returns
produce a meaningless number (sample size, uncorrected multiple
comparisons, lookahead, survivorship, omitted costs, backtest
overfitting) and criticizes FinCon, FinAgent and FinBench by name
(L4.C11). Both are right about different halves — settlement win-rate is
clean, PnL is not — but no shared decomposition exists. **Unresolved.**

**X13 — Does a high score mean saturation or a broken oracle?** Claude
Opus 4.8's 83.5% on OSWorld-Verified exceeds the 72.36% human baseline
(L5.C10). Read one way that is capability; read another, the same
benchmark was hackable (L5.C14) and ~10% of its tasks were broken in
ways including *over-lenient* checks (L5.C8). The two readings are not
distinguishable from a leaderboard. **Unresolved**; L5 notes
evidence-bounded scoring (L5.C22) is the only retrieved method that would
separate them.

**X14 — Is a sponsor-funded benchmark with a holdout trustworthy?**
*Against:* the funder owns the problems, holds most solutions, gated the
disclosure of its own involvement, contributors were not told, and the
non-training term was verbal (L3.D1). *For:* the holdout is real,
enumerable, has been used, and the evidence it produced points the other
way — GPT-5.2 Pro scored 50% on held-out Tier 4 problems against 18% on
sponsor-visible ones, and Epoch reported "no evidence of over-fitting".
**Unresolved.** A null result on 20 problems is weak evidence and the
structural conflict is untouched by it. *Independence note:* L2 and L3
both reached this and **share an upstream** (Epoch's own clarification
post, L2.S23 = L3.S1), so their agreement is not independent convergence.

**X15 — Does procedural generation resist memorization or resist
saturation?** BALROG claims procedural generation means "encountering the
same instance twice is unlikely" (an instance-memorization argument)
while its own leaderboard shows procedurally generated NetHack rising
1.57% → 40.0%; Procgen's result — agents overfit until the generator
supplies ~10⁴ levels — suggests instance novelty is necessary and not
sufficient (L6.D4). **Unresolved as a framing dispute**; F7 records the
distinction rather than the resolution.

**X16 — Is SWE-bench Pro a valid successor?** Scale presents it as
contamination-resistant (copyleft corpus, private + held-out splits,
three human checkpoints); DeepSWE, Poolside and an open maintainer issue
present its public containers as trivially exploitable with a 32.4%
verifier-disagreement rate, and trade press reports OpenAI retracted its
recommendation over ~30% broken tasks (L1.D1). The maintainer has not
publicly responded on the issue. **Unresolved.**

**X17 — Does human screening fix a mined benchmark?** SWE-bench
Verified's premise is yes (500 engineer-screened instances); three
independent studies find leakage, memorization and inadequate tests
surviving the screen (L1.D3). No source claims screening is worthless —
only that it addresses under-specification and not contamination.
**Unresolved.**

**X18 — Does length control remove a bias or remove a signal?** LC raises
Spearman with the human reference 0.94 → 0.98 and style control reshuffles
the board; against that, for some tasks a longer answer genuinely is
better, and LMArena publishes *both* boards rather than replacing one
(L7.D4). No retrieved source measures how often length is diagnostic.
**Unresolved.**

**X19 — Adaptive testing versus comparability.** IRT-guided adaptive
selection dominates fixed-set evaluation on validity, variance,
efficiency and saturation (L8.C17); question-level paired differences,
the cheapest comparison method, require both systems to answer the *same*
items (L8.C16). Neither source acknowledges the trade (L8.D8).
**Unresolved.**

**X20 — What does "84.9% on GDPval" mean?** OpenAI's GPT-5.5 launch
reports it; the paper's scale is win / win+tie against human gold, on
which the best model at release was 47.6%; a search snippet attributes a
*lower* pair (31.9% / 34.6%) to the official leaderboard. Three
incompatible numbers, one name, no primary page fetched (L4.D1).
**Unresolved.**

## Gaps

Everything unestablished. Each names what proved it empty.

**G1 — WMT / MQM judge-certification methods: zero coverage.** L7 named
it in its own scope, dropped it after the safety half consumed the
budget, and assessed it as "the field with the longest running human-judge
meta-evaluation… almost certainly contains the most mature answers to
'how do you certify a judge'" (L7.GAP-1). It was **not searched**. The
run's bound was frozen at eight lanes and `orch-deliver` forbids editing
a frozen spec, so widening the bound because a result looked promising —
the exact failure benchmaker's own bound-partitioning law exists to
prevent — was declined. This is the highest-value follow-up in the
report and it bears directly on RF-12.

**G2 — Client-rendered leaderboards blocked current-SOTA retrieval in
every lane that mined one.** Seven of eight lanes hit it; only L8, the
theory lane, did not. The blocked surfaces, by lane: `swebench.com`,
`livecodebench.github.io`, `tbench.ai/leaderboard` (L1.G2, L1.G4);
`arcprize.org/leaderboard`, `epoch.ai/benchmarks` (L2.GAP-2, L2.GAP-4,
L2.GAP-6); `epoch.ai/benchmarks/frontiermath-*`, SciCode,
ScienceAgentBench (L3.G1, L3.G5, L3.G8); `evals.openai.com/gdpval`,
`forecastbench.org/leaderboards/*` (L4.G1, L4.G2); the GAIA HF Space,
`osworld-v1.xlang.ai` (L5.G3, L5.G4); Kaggle Game Arena chess/Werewolf
boards, `textarena.ai` (L6 gaps); `lmarena`, `tatsu-lab.github.io/alpaca_eval`,
`eqbench.com` (L7.GAP-2, L7.GAP-3). Compounding it: `openai.com` returned
**HTTP 403** to four separate lanes (L1.G1, L4.G1, L5.G5, L8.G9), and
`x.com` returned **HTTP 402** to L3 twice. **Consequence:** the register
carries `GAP` in a current-best cell for roughly a third of its rows.
That is a property of the 2026 web, not of the lanes' effort, and it will
worsen. A future run needs a browser-rendering retrieval path, not more
web calls.

**G3 — The AIME-2025 near-duplicate claim, the counterweight to the whole
recency mechanism.** The primary (an X thread) returned HTTP 402 twice.
Recorded UNVERIFIED and quarantined; it is the single most important
unverified claim in the corpus because recency is the cheapest
anti-contamination mechanism and this is its only retrieved refutation
(L3.G9).

**G4 — `pass^k` has no retrieved primary formalization.** Two lanes
failed independently: L5 got the definition in words from the maintainer
blog but the closed form only from a search summary after two PDF fetches
returned undecoded streams (L5.G1); L8 searched for a paper formalizing
pass^k against pass@k and found none (L8.G3). A convergent gap. RF-13
adopts the definition, not a cited estimator.

**G5 — No measured trend in shrinking benchmark lifespan.** The claim is
asserted by maintainers and the strongest systematic study declines to
call its age gradient significant (L8.G1). The individual arcs do not
shorten monotonically. F22 records this; RF-01 rests on the *observed*
arcs, all inside two years, not on a fitted trend.

**G6 — Rerun variance has never been measured on a judged writing or
safety benchmark.** L7 searched for it explicitly. The two variance
figures in this report come from RAG-answer scoring and tool-calling
(L7.GAP-7). Without it, no judged benchmark's reported delta can be
called significant — which is precisely what RF-06 assumes.

**G7 — Inter-annotator agreement is missing wherever the domain is
contestable.** LegalBench, FinanceBench and Vals AI all ship
expert-authored labels in domains defined by expert disagreement and
publish no agreement statistic; only FinQA and GDPval publish both cost
and label stability (L4.C20, L4.C22, L4.G3, L4.G4, L4.G7).

**G8 — Human baselines are absent across the games lane.** BALROG, FLE,
TextArena (beyond a pooled "Humanity" rating), lmgame-Bench and Kaggle
Game Arena publish none; only ARC-AGI-3, Crafter and PokeAgent's speedrun
do. L6 records this as a field-level gap, not a search failure.

**G9 — Auto-calibrated difficulty does not exist for interactive
targets.** L6's targeted search returned only static-item-bank IRT. F20
records it as an open slot in the field and, for benchmaker, a recorded
non-opportunity: ability-targeted item selection is incompatible with a
sealed immutable case set.

**G10 — Maintainer-side incident reports for reward hacking.** L5 found
no maintainer-published incident report or disclosure response for
τ-bench, WebArena or OSWorld; the only documented maintainer response
(τ³ v1.0.1) addresses annotation defects, not exploits (L5.G9). The field
has an audit literature and no disclosure norm.

**G11 — Per-lane gap records.** Every lane recorded the searches that
proved a question empty (A10): L1.G1–G9, L2.GAP-1–GAP-8, L3.G1–G10,
L4.G1–G10, L5.G1–G9, L6 gaps, L7.GAP-1–GAP-8, L8.G1–G10. L2.GAP-8 (no
primary maintainer publication for any Mensa/IQ-style LLM tracker) and
L4.G9 (the seed set's "APEX" could not be disambiguated against any
primary) are recorded as **empty answers**, not as unfinished work.

**G12 — Benchmaker's own numbers.** The incumbent's net 27/32 is on a
**retired** 12-case set. The current 16-case set at
`sha256:0509fe44…4a660787` has never been consumed by a campaign, so this
report advises on a headroom figure that does not exist yet. RF-01 and
RF-03 are the instruments that would produce it; nothing here substitutes
for running them.

## Sources

Merged and deduplicated across the eight lanes. Ids are lane-scoped so
that any claim in this report resolves to exactly one row, and so that a
convergence claim can be checked for shared upstreams (A12): a row whose
id cell reads `Lx.Sn = Ly.Sm` is **one source two lanes reached
separately**, and any convergence resting only on it is not independent.
Nine such rows exist. Every row carries a URL and a retrieval date (A1);
all retrievals are **2026-08-08**. `primary` follows the run's source
policy: a vendor-published score is primary-but-vendor-reported only
where the vendor made the system scored; aggregators were used to locate
primaries and are cited for no score anywhere in this report.

| id | title | URL | retrieved | primary |
|---|---|---|---|---|
| L1.S1 | SWE-bench leaderboards | https://www.swebench.com/ | 2026-08-08 | yes (scores client-rendered, not retrieved) |
| L1.S2 | SWE-bench/experiments — submission & validation README | https://raw.githubusercontent.com/SWE-bench/experiments/main/README.md | 2026-08-08 | yes |
| L1.S3 | Terminal-Bench 2.0 leaderboard | https://www.tbench.ai/leaderboard/terminal-bench/2.0 | 2026-08-08 | yes |
| L1.S4 | Terminal-Bench 2.1 release notes | https://www.tbench.ai/news/terminal-bench-2-1 | 2026-08-08 | yes |
| L1.S5 | Terminal-Bench: Benchmarking Agents on Hard, Realistic Tasks in CLIs (arXiv 2601.11868) | https://arxiv.org/abs/2601.11868 | 2026-08-08 | yes |
| L1.S6 | Aider LLM leaderboards (polyglot) | https://aider.chat/docs/leaderboards/ | 2026-08-08 | yes |
| L1.S7 | LiveCodeBench leaderboard | https://livecodebench.github.io/leaderboard.html | 2026-08-08 | yes (scores client-rendered, not retrieved) |
| L1.S8 | SWE-bench Pro public leaderboard (Scale) | https://labs.scale.com/leaderboard/swe_bench_pro_public | 2026-08-08 | yes |
| L1.S10 | Anthropic — Claude Opus 5 | https://www.anthropic.com/news/claude-opus-5 | 2026-08-08 | yes, vendor-reported |
| L1.S11 | DeepSWE: Measuring Frontier Coding Agents on Original, Long-Horizon Engineering Tasks (arXiv 2607.07946) | https://arxiv.org/html/2607.07946v1 | 2026-08-08 | yes |
| L1.S12 | "Git Reward Hacking in SWEBench Pro OSS" — scaleapi/SWE-bench_Pro-os issue #93 | https://github.com/scaleapi/SWE-bench_Pro-os/issues/93 | 2026-08-08 | yes |
| L1.S13 | "Repo State Loopholes During Agentic Evaluation" — SWE-bench issue #465 | https://github.com/SWE-bench/SWE-bench/issues/465 | 2026-08-08 | yes |
| L1.S14 | SWE-Bench+: Enhanced Coding Benchmark for LLMs (arXiv 2410.06992) | https://arxiv.org/abs/2410.06992 | 2026-08-08 | yes (abstract via search index, not direct fetch) |
| L1.S15 | Does SWE-Bench-Verified Test Agent Ability or Model Memory? (arXiv 2512.10218v2) | https://arxiv.org/html/2512.10218v2 | 2026-08-08 | yes |
| L1.S16 | UTBoost: Rigorous Evaluation of Coding Agents on SWE-Bench (arXiv 2506.09289) | https://arxiv.org/abs/2506.09289 | 2026-08-08 | yes |
| L1.S17 | SWE-rebench: Automated Pipeline for Task Collection and Decontaminated Evaluation (arXiv 2505.20411) | https://arxiv.org/abs/2505.20411 | 2026-08-08 | yes |
| L1.S18 | SWE-rebench live leaderboard | https://swe-rebench.com/ | 2026-08-08 | yes |
| L1.S19 | SWE-Lancer: Can Frontier LLMs Earn $1 Million from Real-World Freelance SWE? (arXiv 2502.12115) | https://arxiv.org/abs/2502.12115 | 2026-08-08 | yes (partial — PDF returned metadata only) |
| L1.S20 | bigcode-project/bigcodebench (archived read-only 2026-07-20) | https://github.com/bigcode-project/bigcodebench | 2026-08-08 | yes |
| L1.S21 | OpenAI — Why SWE-bench Verified no longer measures frontier coding capabilities | https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/ | 2026-08-08 | yes — **HTTP 403, body not retrieved** |
| L1.S22 | Trade coverage of OpenAI's SWE-bench Verified deprecation and SWE-bench Pro retraction (officechai, thestack.technology, alphasignal) | see L1.G1 | 2026-08-08 | **no — secondary; cited for no score** |
| L1.S23 | Commit0: Library Generation from Scratch (arXiv 2412.01769) | https://arxiv.org/abs/2412.01769 | 2026-08-08 | yes (via search index) |
| L1.S24 | Agent-as-a-Judge: Evaluate Agents with Agents / DevAI (arXiv 2410.10934) | https://arxiv.org/abs/2410.10934 | 2026-08-08 | yes (via search index) |
| L1.S25 | SWE-smith: Scaling Data for Software Engineering Agents (arXiv 2504.21798) | https://arxiv.org/pdf/2504.21798 | 2026-08-08 | yes (via search index) |
| L1.S26 | Poolside — "Through the looking glass of benchmark hacking" | https://poolside.ai/blog/through-the-looking-glass | 2026-08-08 | yes (first-party report; located, not fetched) |
| L2.S1 | ARC-AGI-2 benchmark page | https://arcprize.org/arc-agi/2/ | 2026-08-08 | yes |
| L2.S2 | ARC-AGI-2: A New Challenge for Frontier AI Reasoning Systems (technical report) | https://arcprize.org/blog/arc-agi-2-technical-report | 2026-08-08 | yes |
| L2.S3 | Announcing ARC-AGI-2 and ARC Prize 2025 | https://arcprize.org/blog/announcing-arc-agi-2-and-arc-prize-2025 | 2026-08-08 | yes |
| L2.S4 | ARC Prize 2025 Results and Analysis (pub. 2025-12-05) | https://arcprize.org/blog/arc-prize-2025-results-analysis | 2026-08-08 | yes |
| L2.S5 | ARC Prize 2026 — ARC-AGI-2 Competition | https://arcprize.org/competitions/2026/arc-agi-2 | 2026-08-08 | yes |
| L2.S6 | ARC Prize Verified Testing Policy | https://arcprize.org/policy | 2026-08-08 | yes |
| L2.S7 | ARC-AGI-1 benchmark page | https://arcprize.org/arc-agi/1/ | 2026-08-08 | yes |
| L2.S8 | Measuring Human Performance on ARC-AGI-3 | https://arcprize.org/blog/arc-agi-3-human-dataset | 2026-08-08 | yes |
| **L2.S9 = L6.S2** | ARC-AGI-3: A New Challenge for Frontier Agentic Intelligence (arXiv 2603.24621) | https://arxiv.org/abs/2603.24621 · https://arxiv.org/html/2603.24621v1 | 2026-08-08 | yes |
| **L2.S10 ≈ L8.S21** | ARC-AGI-2 (arXiv 2505.11831) — L2 read the abstract, L8 the HTML v2 | https://arxiv.org/abs/2505.11831 · https://arxiv.org/html/2505.11831v2 | 2026-08-08 | yes |
| L2.S11 | Humanity's Last Exam official site | https://lastexam.ai/ | 2026-08-08 | yes |
| **L2.S12 ≈ L8.S3** | Humanity's Last Exam (arXiv 2501.14249) — L2 read HTML v3, L8 the abs page and HTML v1 | https://arxiv.org/html/2501.14249v3 · https://arxiv.org/abs/2501.14249 | 2026-08-08 | yes |
| L2.S13 | Scale Labs HLE leaderboard (maintainer) | https://labs.scale.com/leaderboard/humanitys_last_exam | 2026-08-08 | yes |
| L2.S14 | cais/hle-rolling dataset card | https://huggingface.co/datasets/cais/hle-rolling | 2026-08-08 | yes |
| **L2.S15 = L8.S18** | FutureHouse — About 30% of Humanity's Last Exam Answers are Wrong (two paths to one audit) | https://www.futurehouse.org/research/hle-exam · https://www.futurehouse.org/research-announcements/hle-exam | 2026-08-08 | yes (independent audit) |
| L2.S16 | HLE-Verified (arXiv 2602.13964v3, 2026-02-27) | https://arxiv.org/html/2602.13964v3 | 2026-08-08 | yes |
| **L2.S17 = L8.S19** | GPQA: A Graduate-Level Google-Proof Q&A Benchmark (arXiv 2311.12022) | https://arxiv.org/abs/2311.12022 | 2026-08-08 | yes (abstract only) |
| **L2.S18 = L8.S2** | MMLU-Pro: A More Robust and Challenging Multi-Task Language Understanding Benchmark (arXiv 2406.01574) | https://arxiv.org/abs/2406.01574 | 2026-08-08 | yes (abstract only) |
| L2.S19 | BIG-Bench Extra Hard (arXiv 2502.19187) | https://arxiv.org/abs/2502.19187 | 2026-08-08 | yes (abstract only) |
| L2.S20 | SimpleBench official site | https://simple-bench.com/ | 2026-08-08 | yes |
| L2.S21 | ZebraLogic (arXiv 2502.01100) | https://arxiv.org/abs/2502.01100 | 2026-08-08 | yes (abstract only) |
| L2.S22 | MMLU-Redux (arXiv 2406.04127) | https://arxiv.org/abs/2406.04127 | 2026-08-08 | yes (abstract only) |
| **L2.S23 = L3.S1** | Epoch AI — Clarifying the creation and use of the FrontierMath benchmark (2025-01-23) | https://epoch.ai/latest/openai-and-frontiermath | 2026-08-08 | yes (maintainer statement) |
| L2.S24 | FrontierMath landing + Tiers 1-4 pages | https://epoch.ai/frontiermath · https://epoch.ai/frontiermath/tiers-1-4 | 2026-08-08 | yes |
| **L2.S25 = L3.S8** | Epoch AI benchmarking hub | https://epoch.ai/benchmarks | 2026-08-08 | yes (scores client-rendered, not retrieved) |
| L2.S26 | NPR Sunday Puzzle benchmark (arXiv 2502.01584) | https://arxiv.org/pdf/2502.01584 | 2026-08-08 | **no — search-engine summary only; design principle carried, numbers not** |
| L3.S2 | Epoch AI — FrontierMath Tiers 1-4, About | https://epoch.ai/frontiermath/tiers-1-4/about | 2026-08-08 | yes |
| L3.S3 | Epoch AI — FrontierMath Tier 4 (v2) benchmark page | https://epoch.ai/benchmarks/frontiermath-tier-4 | 2026-08-08 | yes |
| L3.S4 | Epoch AI — FrontierMath Tier 4: Battle Royale (2025-10-13) | https://epochai.substack.com/p/frontiermath-tier-4-battle-royale | 2026-08-08 | yes |
| L3.S5 | Epoch AI — New record on FrontierMath Tier 4 (2026-01-23) | https://epochai.substack.com/p/new-record-on-frontiermath-tier-4 | 2026-08-08 | yes |
| L3.S6 | Epoch AI — Less than 70% of FrontierMath is within reach for today's models (2025-10-17) | https://epoch.ai/gradient-updates/less-than-70-percent-of-frontiermath-is-within-reach-for-todays-models | 2026-08-08 | yes |
| L3.S7 | Epoch AI — FrontierMath: Open Problems | https://epoch.ai/frontiermath/open-problems | 2026-08-08 | yes |
| L3.S9 | MathArena leaderboard | https://matharena.ai/ | 2026-08-08 | yes |
| L3.S10 | MathArena: Evaluating LLMs on Uncontaminated Math Competitions (arXiv 2505.23281v3) | https://arxiv.org/html/2505.23281v3 | 2026-08-08 | yes |
| L3.S11 | Beyond Benchmarks: MathArena as an Evaluation Platform (arXiv 2605.00674) | https://arxiv.org/abs/2605.00674 | 2026-08-08 | yes |
| L3.S12 | Proof or Bluff? Evaluating LLMs on 2025 USA Math Olympiad (arXiv 2503.21934) | https://arxiv.org/abs/2503.21934 | 2026-08-08 | yes |
| L3.S13 | MathArena Apex | https://matharena.ai/apex/ | 2026-08-08 | yes |
| L3.S14 | MathArena — Farewell to Final-Answer Competition Problems as Frontier Benchmarks | https://matharena.ai/no_final_answer/ | 2026-08-08 | yes |
| L3.S15 | Google DeepMind — Gemini with Deep Think officially achieves gold-medal standard at the IMO | https://deepmind.google/discover/blog/advanced-version-of-gemini-with-deep-think-officially-achieves-gold-medal-standard-at-the-international-mathematical-olympiad/ | 2026-08-08 | yes, vendor-reported (score IMO-certified) |
| L3.S16 | Putnam-AXIOM: A Functional and Static Benchmark for Higher Level Mathematical Reasoning (arXiv 2508.08292) | https://arxiv.org/abs/2508.08292 | 2026-08-08 | yes |
| L3.S17 | Probing the Critical Point (CritPt) of AI Reasoning: a Frontier Physics Research Benchmark (arXiv 2509.26574v3) | https://arxiv.org/html/2509.26574v3 | 2026-08-08 | yes |
| L3.S18 | SciCode project site + paper (arXiv 2407.13168) | https://scicode-bench.github.io/ · https://arxiv.org/abs/2407.13168 | 2026-08-08 | yes |
| L3.S19 | LAB-Bench: Measuring Capabilities of Language Models for Biology Research (arXiv 2407.10362) | https://arxiv.org/abs/2407.10362 | 2026-08-08 | yes |
| L3.S20 | ScienceAgentBench project site (OSU NLP Group) | https://osu-nlp-group.github.io/ScienceAgentBench/ | 2026-08-08 | yes |
| L3.S21 | OlympiadBench (arXiv 2402.14008) | https://arxiv.org/abs/2402.14008 | 2026-08-08 | yes |
| L3.S22 | TechCrunch — AI benchmarking organization criticized for waiting to disclose funding from OpenAI (2025-01-19) | https://techcrunch.com/2025/01/19/ai-benchmarking-organization-criticized-for-waiting-to-disclose-funding-from-openai/ | 2026-08-08 | **no — reporting; used for narrative and the verbal-agreement detail, never a score** |
| L3.S23 | Epoch AI posts on X reporting FrontierMath records | https://x.com/EpochAIResearch/status/1991945942174761050 · .../2029626255776395425 | 2026-08-08 | **maintainer-authored but retrieved only as search renderings — PROVISIONAL; the figures it carries are quarantined** |
| L3.S24 | miniF2F saturation / Seed-Prover; PutnamBench 672 problems | located via search; primary leaderboard not fetched | 2026-08-08 | **no — snippet only; the 99.6% figure is quarantined** |
| **L4.S1 (+ L4.S2)** | GDPval: Evaluating AI Model Performance on Real-World Economically Valuable Tasks (arXiv 2510.04374, HTML + abs) | https://arxiv.org/html/2510.04374 · https://arxiv.org/abs/2510.04374 | 2026-08-08 | yes |
| L4.S3 | GDPval-AA v2 Leaderboard, Artificial Analysis | https://artificialanalysis.ai/evaluations/gdpval-aa | 2026-08-08 | yes (maintainer of that variant) |
| L4.S4 | GDPval page, Epoch AI | https://epoch.ai/benchmarks/gdpval | 2026-08-08 | **no — restates the public leaderboard** |
| L4.S5 | ForecastBench: A Dynamic Benchmark of AI Forecasting Capabilities (arXiv 2409.19839) | https://arxiv.org/html/2409.19839 | 2026-08-08 | yes |
| L4.S6 | ForecastBench explore page (maintainer) | https://www.forecastbench.org/explore/ | 2026-08-08 | yes |
| L4.S7 | "AI models have likely reached parity with superforecasters on ForecastBench" (Forecasting Research Institute) | https://forecastingresearch.substack.com/p/ai-models-have-likely-reached-parity | 2026-08-08 | yes (maintainer post) |
| L4.S8 | Prediction Arena: Benchmarking AI Models on Real-World Prediction Markets (arXiv 2604.07355v1) | https://arxiv.org/html/2604.07355v1 | 2026-08-08 | yes |
| L4.S9 | FinanceBench: A New Benchmark for Financial Question Answering (arXiv 2311.11944) | https://arxiv.org/abs/2311.11944 | 2026-08-08 | yes (abstract) |
| L4.S10 | Finance Agent Benchmark (Vals AI) (arXiv 2508.00828) | https://arxiv.org/abs/2508.00828 | 2026-08-08 | yes (abstract; PDF not text-extractable on this host) |
| L4.S11 | Finance Agent v2 leaderboard, Vals AI (snapshot 2026-08-05) | https://www.vals.ai/benchmarks/fabv2 | 2026-08-08 | yes |
| L4.S12 | OpenAI "Introducing GPT-5.5" (GDPval 84.9%) | https://openai.com/index/introducing-gpt-5-5/ | 2026-08-08 | yes, vendor-reported — **reached via domain-restricted search; page not fetched; metric definition unknown** |
| L4.S13 | FinQA: A Dataset of Numerical Reasoning over Financial Data (ar5iv full text) | https://ar5iv.labs.arxiv.org/html/2109.00122 | 2026-08-08 | yes |
| L4.S14 | FinBen: A Holistic Financial Benchmark for LLMs (arXiv 2402.12659) | https://arxiv.org/abs/2402.12659 | 2026-08-08 | yes (abstract) |
| L4.S15 | Reported Alpha from LLM Trading Agents Should Not Be Trusted (arXiv 2605.16895) | https://arxiv.org/pdf/2605.16895 | 2026-08-08 | yes |
| L4.S16 | BizBench: A Quantitative Reasoning Benchmark for Business and Finance (arXiv 2311.06602) | https://arxiv.org/abs/2311.06602 | 2026-08-08 | yes (abstract; marked "work in progress") |
| L4.S17 | FinVerBench: Benchmark Validity and Calibration in LLM Financial Statement Verification (arXiv 2605.29586v1) | https://arxiv.org/html/2605.29586v1 | 2026-08-08 | yes |
| L4.S18 | LegalBench: A Collaboratively Built Benchmark for Measuring Legal Reasoning (arXiv 2308.11462) | https://arxiv.org/abs/2308.11462 | 2026-08-08 | yes (abstract) |
| L4.S19 | When Does Pretraining Help? … and the CaseHOLD Dataset (arXiv 2104.08671) | https://arxiv.org/abs/2104.08671 | 2026-08-08 | yes (abstract) |
| L4.S20 | Magesh et al. — hallucination-free legal research tools audit (arXiv 2405.20362) | https://arxiv.org/abs/2405.20362 | 2026-08-08 | yes (abstract) |
| L4.S21 | Vals AI benchmark index | https://www.vals.ai/benchmarks | 2026-08-08 | yes |
| L5.S1 | τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains (arXiv 2406.12045) | https://arxiv.org/abs/2406.12045 | 2026-08-08 | yes |
| L5.S2 | Sierra — 𝜏-Bench: Benchmarking AI agents for the real-world (2024-06-20) | https://sierra.ai/blog/benchmarking-ai-agents | 2026-08-08 | yes (maintainer) |
| L5.S3 | sierra-research/tau-bench (README + leaderboard tables) | https://github.com/sierra-research/tau-bench | 2026-08-08 | yes (maintainer) |
| L5.S4 | sierra-research/tau2-bench — now τ³-bench (README, release notes v1.0.1) | https://github.com/sierra-research/tau2-bench | 2026-08-08 | yes (maintainer) |
| L5.S5 | τ-bench Task Schema & Evaluation doc | https://raw.githubusercontent.com/sierra-research/tau2-bench/main/docs/evaluation.md | 2026-08-08 | yes (maintainer) |
| L5.S6 | taubench.com leaderboard (τ², τ³-Banking, τ³-Voice) | https://taubench.com | 2026-08-08 | yes (maintainer) |
| L5.S7 | τ²-Bench: Evaluating Conversational Agents in a Dual-Control Environment (arXiv 2506.07982), read via alphaXiv | https://www.alphaxiv.org/overview/2506.07982v1 | 2026-08-08 | **no — mediated rendering of a primary; its numbers need confirmation** |
| L5.S8 | τ-Bench Verified / SABER (Cuadron et al., arXiv 2512.07850v1) | https://arxiv.org/html/2512.07850v1 | 2026-08-08 | yes |
| L5.S9 | amazon-agi/tau2-bench-verified | https://github.com/amazon-agi/tau2-bench-verified | 2026-08-08 | yes (maintainer) |
| L5.S10 | OSWorld (arXiv 2404.07972) | https://arxiv.org/abs/2404.07972 | 2026-08-08 | yes |
| L5.S11 | XLANG Lab — Introducing OSWorld-Verified (2025-07-28) | https://xlang.ai/blog/osworld-verified | 2026-08-08 | yes (maintainer) |
| L5.S12 | Epoch AI — What does OSWorld tell us about AI's ability to use computers? (2025-10-30) | https://epoch.ai/blog/what-does-osworld-tell-us-about-ais-ability-to-use-computers | 2026-08-08 | yes (for Epoch's own audit) |
| L5.S13 | OSWorld 2.0: Benchmarking Computer Use Agents on Long-Horizon Real-World Tasks (arXiv 2606.29537v1) | https://arxiv.org/html/2606.29537v1 | 2026-08-08 | yes |
| L5.S14 | xlang-ai/OSWorld-V2 (release `osworld-v2-2026.06.24`, manifest pinning) | https://github.com/xlang-ai/OSWorld-V2 | 2026-08-08 | yes (maintainer) |
| L5.S15 | Computer Use at the Edge of the Statistical Precipice (arXiv 2605.08261) | https://arxiv.org/pdf/2605.08261 | 2026-08-08 | yes (argument extracted; tables not — compressed streams) |
| L5.S16 | WebArena (arXiv 2307.13854; abs + ar5iv full text) | https://arxiv.org/abs/2307.13854 · https://ar5iv.labs.arxiv.org/html/2307.13854 | 2026-08-08 | yes |
| L5.S17 | TheAgentCompany (arXiv 2412.14161v2) | https://arxiv.org/html/2412.14161v2 | 2026-08-08 | yes |
| L5.S18 | ARE: Scaling Up Agent Environments and Evaluations / Gaia2 (arXiv 2509.17158) | https://arxiv.org/abs/2509.17158 | 2026-08-08 | yes |
| L5.S19 | Meta Agents Research Environments — Gaia2 and Leaderboard Submission (docs) | https://facebookresearch.github.io/meta-agents-research-environments/user_guide/gaia2_evaluation.html | 2026-08-08 | yes (maintainer) |
| L5.S20 | GAIA: a benchmark for General AI Assistants (arXiv 2311.12983) | https://arxiv.org/abs/2311.12983 | 2026-08-08 | yes |
| L5.S21 | BrowseComp (arXiv 2504.12516) | https://arxiv.org/abs/2504.12516 | 2026-08-08 | yes (abstract) |
| L5.S22 | WebVoyager (arXiv 2401.13919) | https://arxiv.org/abs/2401.13919 | 2026-08-08 | yes |
| L5.S23 | AndroidWorld (arXiv 2405.14573, rev. 2025-04-06) | https://arxiv.org/abs/2405.14573 | 2026-08-08 | yes |
| L5.S24 | MLE-bench (arXiv 2410.07095) | https://arxiv.org/abs/2410.07095 | 2026-08-08 | yes |
| L5.S25 | RE-Bench (METR, arXiv 2411.15114) | https://arxiv.org/abs/2411.15114 | 2026-08-08 | yes |
| L5.S26 | METR — Recent Frontier Models Are Reward Hacking (2025-06-05) | https://metr.org/blog/2025-06-05-recent-reward-hacking/ | 2026-08-08 | yes (maintainer of RE-Bench/HCAST) |
| L5.S27 | Vending-Bench (arXiv 2502.15840) | https://arxiv.org/abs/2502.15840 | 2026-08-08 | yes |
| L5.S28 | Berkeley Function Calling Leaderboard V3 — Multi-Turn (2024-09-19, upd. 2024-12-10) | https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v3_multi_turn.html | 2026-08-08 | yes (maintainer) |
| L5.S29 | Do Androids Dream of Breaking the Game? Systematically Auditing AI Agent Benchmarks with BenchJack (arXiv 2605.12673v1) | https://arxiv.org/html/2605.12673 | 2026-08-08 | yes |
| L5.S30 | Can Agent Benchmarks Support Their Scores? Evidence-Supported Bounds for Interactive-Agent Evaluation (arXiv 2605.10448) | https://arxiv.org/abs/2605.10448 | 2026-08-08 | yes |
| L5.S31 | CRMArena (arXiv 2411.02305, NAACL 2025) | https://arxiv.org/abs/2411.02305 | 2026-08-08 | yes |
| L5.S32 | Beyond pass@1: A Reliability Science Framework for Long-Horizon LLM Agents (arXiv 2603.29231v1) | https://arxiv.org/pdf/2603.29231 | 2026-08-08 | yes (argument only; tables not extractable) |
| L6.S1 | ARC Prize leaderboard | https://arcprize.org/leaderboard | 2026-08-08 | yes (client-rendered; no figures extractable) |
| L6.S3 | ARC Prize — Claude Opus 5 results page | https://arcprize.org/results/anthropic-claude-opus-5 | 2026-08-08 | yes (benchmark maintainer) |
| L6.S4 | ARC-AGI-3 overview page | https://arcprize.org/arc-agi/3 | 2026-08-08 | yes |
| L6.S5 | TextArena (arXiv 2504.11442) | https://arxiv.org/abs/2504.11442 · https://arxiv.org/html/2504.11442v1 | 2026-08-08 | yes |
| L6.S6 | BALROG: Benchmarking Agentic LLM and VLM Reasoning On Games (arXiv 2411.13543v2) | https://arxiv.org/html/2411.13543v2 | 2026-08-08 | yes |
| L6.S7 | BALROG official leaderboard | https://balrogai.com/ | 2026-08-08 | yes (maintainer) |
| L6.S8 | Insights From the NeurIPS 2021 NetHack Challenge (arXiv 2203.11889) | https://arxiv.org/abs/2203.11889 | 2026-08-08 | yes (abstract only) |
| L6.S9 | Factorio Learning Environment (arXiv 2503.09617v1) | https://arxiv.org/html/2503.09617v1 | 2026-08-08 | yes |
| L6.S10 | lmgame-Bench (arXiv 2505.15146v1) | https://arxiv.org/html/2505.15146v1 | 2026-08-08 | yes |
| L6.S11 | Melting Pot 2.0 (arXiv 2211.13746) | https://arxiv.org/abs/2211.13746 | 2026-08-08 | yes (abstract only) |
| L6.S12 | Scalable Evaluation of MARL with Melting Pot (arXiv 2107.06857) + DeepMind repo | https://arxiv.org/pdf/2107.06857 · https://github.com/google-deepmind/meltingpot | 2026-08-08 | **partial — PDF undecodable; protocol statements from search summaries** |
| L6.S13 | Google blog — Game Arena: Poker and Werewolf, and Gemini 3 tops chess | https://blog.google/innovation-and-ai/models-and-research/google-deepmind/kaggle-game-arena-updates/ | 2026-08-08 | yes (maintainer) |
| L6.S14 | PokerSkill: LLMs Can Play Expert-Level Poker without Training or Solvers (arXiv 2605.30094v1) | https://arxiv.org/html/2605.30094v1 | 2026-08-08 | yes |
| L6.S15 | The PokeAgent Challenge (arXiv 2603.15563v1) | https://arxiv.org/html/2603.15563v1 | 2026-08-08 | yes |
| L6.S16 | Meta AI — CICERO research page (Science 10.1126/science.ade9097; science.org returned 403) | https://ai.meta.com/research/cicero/ | 2026-08-08 | yes, **vendor-reported** |
| L6.S17 | Crafter repository (score formula, achievements, human baseline, leaderboard) | https://github.com/danijar/crafter | 2026-08-08 | yes (maintainer) |
| L6.S18 | Procgen Benchmark (Cobbe et al. 2020) — PMLR PDF undecodable, openai.com 403 | https://proceedings.mlr.press/v119/cobbe20a/cobbe20a.pdf · https://openai.com/index/procgen-benchmark/ | 2026-08-08 | **partial — figures from search summaries; re-verify before load-bearing use** |
| L6.S19 | Gemini Plays Pokemon maintainer statement on non-comparability (relayed) | https://www.lesswrong.com/posts/7mqp8uRnnPdbBzJZE/is-gemini-now-better-than-claude-at-pokemon | 2026-08-08 | **no — quotes a primary statement** |
| L6.S20 | Kaggle Werewolf leaderboard | https://www.kaggle.com/benchmarks/kaggle/werewolf | 2026-08-08 | **partial — client-rendered; methodology text via search summary** |
| L6.S21 | Kaggle Chess Text leaderboard | https://www.kaggle.com/benchmarks/kaggle/chess-text | 2026-08-08 | yes (client-rendered; no figures) |
| L6.S22 | Kaggle blog — Adding Chess Openings to Game Arena | https://www.kaggle.com/blog/game-arena-chess-openings | 2026-08-08 | yes (client-rendered; title only) |
| L6.S23 | Adaptive Testing for LLM Evaluation (ATLAS), arXiv 2511.04689 | https://arxiv.org/abs/2511.04689 | 2026-08-08 | **partial — figures via search summary** |
| L6.S24 | Palisade Research — Demonstrating specification gaming in reasoning models | https://palisaderesearch.org/blog/specification-gaming | 2026-08-08 | yes (no per-model rates on page) |
| L6.S25 | Demonstrating specification gaming in reasoning models (arXiv 2502.13295) | https://arxiv.org/abs/2502.13295 | 2026-08-08 | yes (abstract only) |
| L6.S26 | DeepMind — Specification gaming: the flip side of AI ingenuity | https://deepmind.google/blog/specification-gaming-the-flip-side-of-ai-ingenuity/ | 2026-08-08 | yes |
| L7.S1 | Dubois et al. — Length-Controlled AlpacaEval (arXiv 2404.04475) | https://arxiv.org/abs/2404.04475 | 2026-08-08 | yes |
| L7.S2 | Zheng et al. — Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena (arXiv 2306.05685, ar5iv) | https://ar5iv.labs.arxiv.org/html/2306.05685 | 2026-08-08 | yes |
| L7.S3 | Arena-Hard-Auto maintainer repository incl. v2.0-Preview leaderboard (2025-04-23) | https://github.com/lmarena/arena-hard-auto | 2026-08-08 | yes |
| L7.S4 | Li et al. — From Crowdsourced Data to High-Quality Benchmarks: Arena-Hard and BenchBuilder (arXiv 2406.11939) | https://arxiv.org/abs/2406.11939 | 2026-08-08 | yes (abstract) |
| L7.S5 | AlpacaEval maintainer repository — annotator agreement/price/variance table | https://github.com/tatsu-lab/alpaca_eval | 2026-08-08 | yes |
| L7.S6 | AlpacaEval official leaderboard | https://tatsu-lab.github.io/alpaca_eval/ | 2026-08-08 | yes (rows client-rendered, not retrieved) |
| L7.S7 | Arora et al. (OpenAI) — HealthBench (arXiv 2505.08775v1) | https://arxiv.org/html/2505.08775v1 | 2026-08-08 | yes (model scores vendor-reported) |
| L7.S8 | Starace et al. (OpenAI) — PaperBench (arXiv 2504.01848v2) | https://arxiv.org/html/2504.01848v2 | 2026-08-08 | yes (vendor-reported) |
| L7.S9 | EQ-Bench Creative Writing v3 maintainer repository | https://github.com/EQ-bench/creative-writing-bench | 2026-08-08 | yes |
| L7.S10 | Souly et al. — A StrongREJECT for Empty Jailbreaks (arXiv 2402.10260v2) | https://arxiv.org/html/2402.10260v2 | 2026-08-08 | yes |
| L7.S11 | Mazeika et al. — HarmBench (arXiv 2402.04249v2) | https://arxiv.org/html/2402.04249v2 | 2026-08-08 | yes |
| L7.S12 | AgentHarm implementation in UK AISI `inspect_evals` | https://github.com/UKGovernmentBEIS/inspect_evals/tree/main/src/inspect_evals/agentharm | 2026-08-08 | yes (authoritative for current behavior) |
| L7.S13 | Andriushchenko et al. — AgentHarm (arXiv 2410.09024) | https://arxiv.org/abs/2410.09024 | 2026-08-08 | yes (abstract; HTML v1/v2/v3 all 404) |
| L7.S14 | Chiang et al. — Chatbot Arena: An Open Platform for Evaluating LLMs by Human Preference (arXiv 2403.04132v1) | https://arxiv.org/html/2403.04132v1 | 2026-08-08 | yes |
| L7.S15 | LMSYS Org — Does style matter? Disentangling style and substance in Chatbot Arena (2024-08-29) | https://www.lmsys.org/blog/2024-08-28-style-control/ | 2026-08-08 | yes (maintainer blog) |
| **L7.S16 = L8.S27** | Singh et al. — The Leaderboard Illusion (arXiv 2504.20879) | https://arxiv.org/abs/2504.20879 | 2026-08-08 | yes (L7 read an abstract-level search extract; L8 the abs page) |
| L7.S17 | Wu et al. — WritingBench (arXiv 2503.05244v2) | https://arxiv.org/html/2503.05244v2 | 2026-08-08 | yes |
| L7.S18 | Panickssery et al. — LLM Evaluators Recognize and Favor Their Own Generations (arXiv 2404.13076v1) | https://arxiv.org/html/2404.13076v1 | 2026-08-08 | yes |
| L7.S19 | strong_reject package documentation — evaluator registry | https://strong-reject.readthedocs.io/en/latest/api/evaluate.html | 2026-08-08 | yes (maintainer docs) |
| L7.S20 | Chao et al. — JailbreakBench (arXiv 2404.01318) | https://arxiv.org/abs/2404.01318 | 2026-08-08 | yes (abstract) |
| L7.S21 | Chao et al. — JailbreakBench, NeurIPS 2024 D&B proceedings PDF | https://proceedings.neurips.cc/paper_files/paper/2024/file/63092d79154adebd7305dfd498cbff70-Paper-Datasets_and_Benchmarks_Track.pdf | 2026-08-08 | yes — **PDF would not convert; classifier-agreement figures from a search extract** |
| L7.S22 | Lau — Same Input, Different Scores: A Multi-Model Study on the Inconsistency of LLM Judges (arXiv 2603.04417) | https://arxiv.org/abs/2603.04417 | 2026-08-08 | yes (abstract-level only) |
| L7.S23 | Bai et al. — LongWriter / LongBench-Write (arXiv 2408.07055) | https://arxiv.org/abs/2408.07055 | 2026-08-08 | yes (abstract-level only) |
| L7.S24 | BAIR blog — How to Evaluate Jailbreak Methods: A Case Study with StrongREJECT (2024-08-28) | https://bair.berkeley.edu/blog/2024/08/28/strong-reject/ | 2026-08-08 | yes (author-affiliated; formula read from a search extract) |
| L7.S25 | dsbowen/strong_reject maintainer repository | https://github.com/dsbowen/strong_reject | 2026-08-08 | yes |
| L7.S26 | Benchmarking the Benchmarks: A Validity Audit of Tool-Calling Evaluation (arXiv 2607.02577) | https://arxiv.org/pdf/2607.02577 | 2026-08-08 | yes — **figures from a search extract; different domain, cited only for the magnitude of rerun variance** |
| L8.S1 | SuperGLUE: A Stickier Benchmark for General-Purpose Language Understanding Systems | https://arxiv.org/pdf/1905.00537 | 2026-08-08 | yes (the RoBERTa/DeBERTa timeline via search summary — L8.G7, provisional) |
| L8.S4 | Ofir Press — How to Build Good Language Modeling Benchmarks (Aug 2024, edited Jan 2025 and May 2025) | https://ofir.io/How-to-Build-Good-Language-Modeling-Benchmarks/ | 2026-08-08 | yes (maintainer) |
| L8.S5 | Ott et al. — Mapping global dynamics of benchmark creation and saturation in AI (Nature Communications 2022) | https://pmc.ncbi.nlm.nih.gov/articles/PMC9649641/ | 2026-08-08 | yes |
| L8.S6 | When AI Benchmarks Plateau: A Systematic Study of Benchmark Saturation (arXiv 2602.16763) | https://arxiv.org/html/2602.16763 | 2026-08-08 | yes |
| L8.S7 | Alignment Research Center — Evaluations Canary | https://www.alignment.org/canary/ | 2026-08-08 | yes (maintainer doc) |
| L8.S8 | BIG-Bench Canary Contamination in GPT-4 | https://www.alignmentforum.org/posts/kSmHMoaLKGcGgyWzs/big-bench-canary-contamination-in-gpt-4 | 2026-08-08 | yes (original empirical write-up) |
| L8.S9 | Rethinking Benchmark and Contamination for Language Models with Rephrased Samples (arXiv 2311.04850) | https://arxiv.org/abs/2311.04850 | 2026-08-08 | yes |
| L8.S10 | LiveCodeBench: Holistic and Contamination Free Evaluation of LLMs for Code (arXiv 2403.07974v2) | https://arxiv.org/html/2403.07974v2 | 2026-08-08 | yes |
| L8.S11 | LiveBench: A Challenging, Contamination-Free LLM Benchmark (arXiv 2406.19314) | https://arxiv.org/abs/2406.19314 | 2026-08-08 | yes |
| L8.S12 | Humanity's Last Exam official site and leaderboard (CAIS / Scale AI) | https://agi.safe.ai/ | 2026-08-08 | yes (maintainer) |
| L8.S13 | A Careful Examination of LLM Performance on Grade School Arithmetic (GSM1k) (arXiv 2405.00332) | https://arxiv.org/abs/2405.00332 | 2026-08-08 | yes |
| L8.S14 | Raji et al. — AI and the Everything in the Whole Wide World Benchmark (arXiv 2111.15366) | https://arxiv.org/abs/2111.15366 | 2026-08-08 | yes (abstract only) |
| L8.S15 | Wallach et al. — Position: Evaluating Generative AI Systems Is a Social Science Measurement Challenge (ICML 2025, arXiv 2502.00561v1) | https://arxiv.org/html/2502.00561v1 | 2026-08-08 | yes |
| L8.S16 | BetterBench: Assessing AI Benchmarks, Uncovering Issues, and Establishing Best Practices (NeurIPS 2024, arXiv 2411.12990v1) | https://arxiv.org/html/2411.12990v1 | 2026-08-08 | yes |
| L8.S17 | Liang et al. — Holistic Evaluation of Language Models (HELM) (arXiv 2211.09110) | https://arxiv.org/abs/2211.09110 | 2026-08-08 | yes |
| L8.S20 | Epoch AI — Epoch Capabilities Index (ECI) | https://epoch.ai/eci | 2026-08-08 | yes (maintainer; the MMLU-Pro 89.87/90.10 figures came via search summary and are **unconfirmed**) |
| L8.S22 | Miller — Adding Error Bars to Evals: A Statistical Approach to Language Model Evaluations (arXiv 2411.00640v1) | https://arxiv.org/html/2411.00640v1 | 2026-08-08 | yes |
| L8.S23 | tinyBenchmarks: evaluating LLMs with fewer examples (arXiv 2402.14992) | https://arxiv.org/abs/2402.14992 | 2026-08-08 | yes (abstract only) |
| L8.S24 | Hofmann et al. — Fluid Language Model Benchmarking (arXiv 2509.11106v1) | https://arxiv.org/html/2509.11106v1 | 2026-08-08 | yes |
| L8.S25 | Epoch AI — A Rosetta Stone for AI Benchmarks | https://epoch.ai/publications/a-rosetta-stone-for-ai-benchmarks | 2026-08-08 | yes (maintainer) |
| L8.S26 | Land & Bikel — Auditing LLM Benchmarks with Item Response Theory (arXiv 2605.30504) | https://arxiv.org/pdf/2605.30504 | 2026-08-08 | yes (structure and benchmark list only; body figures not extractable) |
| L8.S28 | OpenAI — Monitoring Reasoning Models for Misbehavior and the Risks of Promoting Obfuscation (arXiv 2503.11926) | https://arxiv.org/abs/2503.11926 | 2026-08-08 | yes |
| L8.S29 | ARC Prize — What is ARC-AGI? | https://arcprize.org/arc-agi | 2026-08-08 | yes (maintainer; no launch-score target on the page) |

**Sources reached but unusable, recorded for provenance.**
`openai.com/index/gdpval/` (HTTP 403), `evals.openai.com/gdpval` (rendered
without leaderboard content), `cdn.openai.com/pdf/.../GDPval.pdf`
(exceeded fetch size), `aclanthology.org/2025.finnlp-2.15.pdf` (SEC-QA;
PDF returned as binary, `pdftoppm` not installed on this host),
`openai.com/index/browsecomp/` (HTTP 403),
`openai.com/index/chain-of-thought-monitoring/` (HTTP 403),
`futurehouse.org/lab-bench` (404), `blog.lmarena.ai` → `arena.ai/blog/...`
(404), `arxiv.org/pdf/2406.12045` (undecoded FlateDecode streams, twice),
`ar5iv.labs.arxiv.org/html/2406.12045` (fatal conversion error),
`arxiv.org/html/2410.09024{v1,v2,v3}` (404),
`arxiv.org/html/2605.30504v1` (404),
`x.com/DimitrisPapail/status/1888325914603516214` (HTTP 402),
`science.org` for the CICERO paper (403), `arxiv.org/abs/2412.04604`
(ARC Prize 2024 technical report; text extraction failed twice).

**Aggregators.** llm-stats, benchlm, morphllm, steel.dev, codeant,
vals.ai (as an aggregator, distinct from L4.S11's maintainer board),
artificialanalysis (as an aggregator, distinct from L3.G7's own
measurement), snorkel, gdpval.pro, bracai, DataLearner, Our World in
Data, emergentmind. Used **only** to locate primaries. Cited for no score
in this report.

## Next

1. **Run RF-01 and RF-03 before anything else.** Both are measurements,
   not changes: score the incumbent against the candidate-accessible
   scope of the sealed 16-case set and record the separation across two
   candidate rungs. Until those figures exist, every other row is advice
   about a benchmark whose difficulty is unmeasured (G12) — and both are
   recorded, not gated, so neither can fail and force a set revision.
2. **Spawn the WMT/MQM lane as a bounded follow-up run** (G1). It is the
   one named vein with zero coverage and it owns the evidence RF-12
   needs. It is the owner's call, not this run's — the bound was frozen
   at eight lanes and staying inside it was the correct ruling.
3. **Give the next research run a browser-rendering retrieval path**
   (G2). Roughly a third of this register's current-best cells are `GAP`
   because leaderboards render client-side and `openai.com` returns 403.
   More web calls will not fix that; a different retrieval mechanism
   will.
4. **Take RF-01, RF-02, RF-03, RF-18 and RF-21 to a single supersession
   PR**, since they are one law: difficulty is measured and recorded,
   minimality cannot trade it away, discrimination is proven against real
   candidates, every case declares an anchor outside the package, and the
   arbitration order says which wins when they conflict. Splitting them
   mints five successor identities for one idea.
5. **Send RF-18..RF-21 to a disjoint context for verdicts.** They are the
   only rows in the register whose author and reviewer are the same, and
   A9's guarantee does not extend to them.
6. **Fold the atlas's answer-reachable group and F3 into a pre-seal
   checklist** and run it as an `orch-critique` lens (RF-04), naming it a
   dated checklist. Benchmaker's probes execute in the same tree as the
   packages they grade.
7. **Carry the friction finding forward.** A blind lane's exclusive write
   scope structurally forbids appending to the shared friction log, so
   every parallel lane must hand entries to its spawner and eight lanes
   appending to one file would contend. The worklog records the candidate
   fix (per-lane friction shards merged at the join, or a lane-scoped
   friction path the logger understands); it belongs to
   `orch-self-improve`, not to this report.
