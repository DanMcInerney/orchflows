# The benchmaker case set

Thirteen benchmark-building tasks that exercise the `benchmaker`
composition from every angle it claims to cover. Each case hands
benchmaker a target, the evidence a builder may read, and a cost bound,
and holds back seeded implementations that a qualified benchmark must
separate. A case is passed when the benchmark benchmaker produces
passes every good seed, fails every bad one, and stays inside the
case's bound; the seeds are what turn "benchmaker produced a benchmark"
into "benchmaker produced a benchmark that works".

The set is authored for reuse: `evolve` and `skill-tournament` seal a
B(0) from it, and `drift-canary` replays it when a binding changes.

## The angle matrix

Frozen. One case per row; `validate_cases.py` enforces the bijection.

| angle | what it proves about benchmaker | case |
| --- | --- | --- |
| deterministic-cli | crisp outcome, near-miss mutants | cli-dedupe |
| time-semantics | benchmark must control time injectably | lib-rate-limiter |
| judged-outcome | judged anchors, judged-secondary law | skill-summarize |
| anti-goodhart | produced benchmark catches a hardcoding gamer | overfit-trap |
| refusal | unobservable outcome, stop with gaps, never invent | unobservable-outcome |
| sparse-evidence | gap declaration under thin docs | sparse-evidence |
| contradiction | disagreement register propagates to design | contradictory-evidence |
| multi-domain | chained single-pack materialization (code + doc) | multi-domain |
| stateful | setup/teardown isolation in produced benchmark | stateful-plugin |
| nondeterminism | seed pinning or statistical oracle | nondeterministic-target |
| cost-pressure | smallest evaluation maximizing discrimination in budget | cost-explosion |
| workflow-target | benchmark of a workflow file, the recursion dry run | composition-target |
| ranking | candidate set to a total order: ties, margins, exclusion | candidate-ranking |

## Case package layout

`cases/<id>/` holds `case.toml` (the fourteen frozen schema keys),
`target/` (the tool under benchmark), `evidence/` (everything a builder
may read), `seeds/good*/` and `seeds/bad-<slug>/` (protected ground
truth, each bad seed carrying `defect.md`), and `expected.md` (what a
qualified benchmark must demonstrate). `tools/validate_cases.py` is the
normative statement of the schema, the value types, and the probe
contract — read its module docstring rather than a paraphrase.

The `probe` in `case.toml` is the case author's sanity oracle, not the
benchmark. It exists so the set can prove its own seeds are live before
benchmaker ever runs.

## Protected evidence

Seeds are ground truth. The policy has three parts:

- **Storage is repo-local.** `seeds/` sits beside the case it belongs
  to. Nothing here is encrypted or held out of the checkout.
- **Access is barred by dispatch authority, not by secrecy.** A builder
  or candidate context receives only the paths in the case's `evidence`
  key and its `target/`; `seeds/`, `expected.md` and `probe.py` are
  outside that authority and outside the builder's write scope.
  `validate_cases.py` fails any case whose `evidence` reaches into
  `seeds/`. Qualification runs in a context disjoint from builders, per
  `compositions/references/benchmaker-protocol.md`.
- **True held-out storage is the port hardening, not a property of this
  set.** Anything with checkout access can read the seeds today. Moving
  them behind the bench-stack plugin boundary — installed bytes outside
  this repository — is what makes the protection structural rather than
  procedural. Until then, treat a candidate that has read the repo as
  having seen the seeds, and re-seed before trusting a score from it.

## Port path to bench-stack

A bench-stack plugin is one directory: `benchmark.toml` plus
`adapter.py`, installed outside the repository. Nothing here needs to
move. The port is:

- `benchmark.toml` — plugin identity and case selection, keyed on the
  `angle` and `negative` fields already in each `case.toml`.
- `adapter.py` — walks `cases/*/case.toml`, resolves `target`,
  `evidence` and `bound`, and runs `probe` once per implementation
  directory under the substitution rules in `validate_cases.py`. The
  `port` key in every `case.toml` carries that case's adapter hints.

The set stays port-ready by construction: `case.toml` is the only thing
an adapter must read, every path in it is case-relative, and no target
needs network, Docker, or an external install.

## Running the validator

    uv run --no-project python benchmarks/benchmaker/tools/validate_cases.py

Stdlib only. Exit 0 and silent when the set is clean; exit 1 with one
`ERROR <case-id>: <message>` line per violation. `--cases-dir` points it
at another tree; `--only <case-id>` (repeatable) restricts it to named
cases and, because it then cannot see the whole set, drops the
thirteen-row completeness check — it never stands in for the flagless run,
which is the set's acceptance oracle.
