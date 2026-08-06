# What a qualified benchmark for this target must demonstrate

## 0. What this case is for

This case rehearses benchmark-of-a-workflow: the target is not a
program and not a prose artifact but a workflow file — steps, edges,
invariants, a done check — and the benchmark under construction must
decide its correctness from the file's bytes.

That is the shape benchmaker-on-benchmaker needs. `compositions/`
holds workflow files; `compositions/benchmaker.md` is one. A benchmark
that can decide whether this toy pipeline's artifact chain resolves is
the same instrument, at toy scale, as a benchmark of BenchMaker itself.
Running BenchMaker against this case is therefore the dry run for the
recursion: if BenchMaker cannot build a benchmark for a two-step
pipeline whose defects are all resolvable references, it cannot build
one for itself. Nothing in this case involves BenchMaker as a target —
the recursion is the point of the rehearsal, not its content.

## 1. What the benchmark must decide

Four resolution properties, all decidable from the file's bytes with no
model call, no execution, and no network:

- every edge endpoint resolves to a declared step id;
- every edge's carried artifact resolves to the predecessor step's
  `produces`;
- every declared step id is bound by some invariant clause;
- the done check names the terminal step's artifact and states a
  predicate over it, rather than restating step status.

Plus the frame the shape contract fixes: frontmatter carries `name`,
`description` (≤140 chars) and an `entry` from the closed set; two steps
minimum with unique ids and distinct artifacts; the edges form one chain
covering every step; `Return:` leads with `status, result`.

A benchmark that moves any of these behind a judged criterion is not
qualified. Every one is byte-decidable, so a judged oracle here buys
the judge's variance for nothing — see `evidence/artifact-chain.md`.

## 2. Discrimination, seed by seed

The reference and `seeds/good-three-step/` must pass; each bad seed must
fail, and must fail through the property that owns its defect:

| seed | must be caught by | passes |
| --- | --- | --- |
| bad-unbound-step | every step is bound by an invariant | chain, edges, done check |
| bad-status-done-check | done check names the terminal artifact and predicates over it | steps, edges, invariants |
| bad-broken-edge | carried artifact resolves to the predecessor's produces | every id-graph check |

`bad-broken-edge` is the near-miss and the discrimination test that
matters. Its step-id graph is intact, so a benchmark modeling the
workflow as a graph over step ids scores it clean; only a benchmark that
modeled produces/consumes as a second relation catches it. Qualification
must exhibit that failing run, not assert the capability.

`seeds/good-three-step/` guards the other direction. It varies step
count, entry value, unit names, and artifact names against the
reference, so a benchmark that hardcoded the reference's shape — two
steps, `entry: named`, the artifact name `digest.md` — fails a good seed
and is not qualified. Discrimination is separation, not strictness.

## 3. Qualification verdicts expected

`case.toml`'s `expected_qualification` names the enum values; they mean:

- **discrimination** — both good variants pass, all three bad seeds
  fail, each through its own property per the table above.
- **reproducibility** — the benchmark recomputes identical verdicts from
  the same bytes; with no model in the loop there is no variance to
  budget, so a nondeterministic verdict here is a defect in the
  benchmark, not sampling noise.
- **schema-valid** — the benchmark seals under the manifest schema with
  every component fixed by identity.
- **cost-within-bound** — the run stays inside `case.toml`'s `bound`.
  Parsing five short markdown files is the whole cost; a benchmark that
  needs a model call to decide a resolution question has already missed
  the bound.

## 4. The probe is not the benchmark

`probe.py` is the case author's sanity oracle: it
decides the four resolution properties and the frame, and its passing on
both good variants while failing on each bad seed is evidence that the
seeds are real and isolated — each bad seed trips exactly the failure
its `defect.md` names. It is not evidence that a benchmark exists, and a
produced benchmark that shells out to it has built nothing.
