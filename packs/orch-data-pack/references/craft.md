# Data craft

The shape principles every domain shares are
[rules/token-economy.md](../../../rules/token-economy.md) §10's.

## Vocabulary

- **dataset identity** — one pinned input: source, version or content
  digest, schema, and retrieval date; the only ground a number may
  rest on.
- **pipeline** — the recorded, deterministic path from dataset
  identities to a claimed number; rerunnable by one command, no hand
  steps.
- **load-bearing number** — a number whose change flips the finding;
  each names its pipeline and dataset identities.
- **leakage** — information outside a step's declared inputs reaching
  its result: target in features, test in train, future in past.
- **degrees of freedom** — the analysis choices made after seeing the
  data: filters, thresholds, exclusions, metric picks; recorded as
  spent, because unrecorded choices can find anything.
- **robustness check** — the same question re-asked under a defensibly
  different choice; a finding surviving none is the choice speaking,
  not the data.

## Workspace

git: identities are commits whose committed manifests pin dataset bytes
by digest, raw data living outside the repository; the join
re-materializes any derived output in contention.

## Spec fields

target repository; dataset identities or the pinning policy; the
question; rerun policy; claim bar — the robustness checks every
load-bearing number must survive

## Lens

### root

#### What a frozen data root carries

- One question answerable by numbers or a modeled relationship, never
  "explore the data" — with the sub-questions coverage requires.
- Dataset identities, or the pinning policy that will fix them; a root
  over unpinned data freezes a guess.
- The claim bar as named robustness checks, and the rerun policy that
  makes reproduction possible.

#### Worth asking at intake

- What decision moves on these numbers, and at what precision does it
  stop moving?
- Are the datasets reachable, licensed, and sufficient at the bar — or
  is acquisition its own preceding kind?
- Which choices freeze now — population, window, metric — and which
  stay executor-owned degrees of freedom?
- What would make the answer wrong even with every pipeline green?

#### Exemplar policy

Cite a prior analysis by identity and name each property the imitation
carries: pipeline discipline, uncertainty reporting, robustness set.
"As rigorous as that one" is a mood, not a property list.

### cut

Slice only genuinely separable pipelines — by dataset, population, or
sub-question — or dependency-ordered stages: pinning before analysis, analysis
before the terminal reproduction. Context carries each member's dataset
identities and frozen choices. Every lane materializes its own outputs from
the shared pinned inputs; terminal reproduction reruns every recorded pipeline
and reconciles the findings.

### git

- Reproduction: rerunning each recorded pipeline from its dataset
  identities returns each load-bearing number.
- Leakage: no step's result rests on information outside its declared
  inputs.
- Choices: the recorded degrees of freedom are defensible, and each
  finding survives the robustness checks the claim bar demands.
- Base rates: every comparison names its denominator and baseline; an
  effect is a size, not a direction.
- Provenance: every figure and number traces to a pipeline and dataset
  identity, and the uncertainty reaches the findings, not only the
  raw output.

Identify the candidate revision. Record dataset identities, pipeline commands
with output digests, the fresh reproduction reading for every load-bearing
number, spent degrees of freedom, robustness readings, and unanswered parts
of Goal.

Weigh in listed order: nothing below reproduction holds while the numbers
themselves fail to reproduce.

- Numbers are artifacts: a load-bearing number is materialized by its
  pipeline into the workspace, never hand-copied from output to prose.
- A point value claims too much: every load-bearing number carries its
  spread, interval, or stated caveat.
- Record seeds, versions, and environment wherever they change a number.

## Stages

- Analyze inside the fixed question and dataset identities, recording
  each degree of freedom as it is spent, dead ends included.
- Materialize every load-bearing number through a pipeline before
  citing it; a number living only in prose or a transcript is
  unclaimed.
- Reproduce as the terminal act: rerun every recorded pipeline fresh
  from pinned inputs; a number that does not come back is a finding
  about the pipeline, never a rounding matter.
- Prefer a declared gap over an irreproducible or leaky number.
- Run the narrow affected computation replay; the full suite is the
  gate's row, never a unit's.
- Close with dataset identities, pipeline commands, reproduced numbers
  with uncertainty, and unresolved caveats.
