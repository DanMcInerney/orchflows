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

## Shape

- Numbers are artifacts: a load-bearing number is materialized by its
  pipeline into the workspace, never hand-copied from output to prose.
- A point value claims too much: every load-bearing number carries its
  spread, interval, or stated caveat.
- Record seeds, versions, and environment wherever they change a number.

## Lens

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

## Execute stages

- Analyze inside the fixed question and dataset identities, recording
  each degree of freedom as it is spent, dead ends included.
- Materialize every load-bearing number through a pipeline before
  citing it; a number living only in prose or a transcript is
  unclaimed.
- Reproduce as the terminal act: rerun every recorded pipeline fresh
  from pinned inputs; a number that does not come back is a finding
  about the pipeline, never a rounding matter.
- Prefer a declared gap over an irreproducible or leaky number.
- Close with dataset identities, pipeline commands, reproduced numbers
  with uncertainty, and unresolved caveats.
