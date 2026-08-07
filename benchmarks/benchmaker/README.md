# The benchmaker case set

Sixteen benchmark-building tasks that exercise the `benchmaker`
composition from every angle it claims to cover. This set is the
successor of the thirteen-case hand-authored set (sealed
`sha256:ff7d9aad…6de675d0`, superseded — see SEALS.md): it was
produced end to end by the `benchmaker` composition run against
benchmaker's own fixed identity per `docs/benchmaker.md`
§Self-benchmarking, from a frozen two-lane research synthesis, a
candidate-blind evaluation design, disjoint builder contexts, and an
independent qualification. Every case's `provenance` key traces to
the claim register of that synthesis; the evaluation design and
qualification verdicts ship with the package.

Each case hands benchmaker a target, the evidence a builder may
read, and a cost bound. The artifact under test in most cases is a
REFERENCE BENCHMARK PACKAGE — the thing benchmaker is expected to
produce — and the case's probe scores that package: manifest
identity recomputation, component digests, verdict-contract
compliance, and inner discrimination over a supplied implementation
pool. Seeds are whole-package variants; a case is passed when the
probe passes the reference and every good variant and fails every
bad one.

## The angle matrix

Frozen. One case per row; `tools/validate_cases.py` enforces the
bijection.

| angle | what it proves about benchmaker | case |
| --- | --- | --- |
| deterministic-cli | byte-exact outcome, transcript anchoring, qualification independence | cs-cli-fresh |
| time-semantics | injected-clock scoring, no invented interface surface | cs-ratelimit-fresh |
| judged-outcome | anchored judged split, non-compensating, rerun variance recorded | cs-judged-fresh |
| anti-goodhart | protected policy complete or resistance UNVERIFIED; no exhibited holdback | cs-antigoodhart-2 |
| refusal | blocked return with zero benchmark identities, no proxy oracle | cs-refusal-2 |
| sparse-evidence | every criterion evidence-traced, gaps declared, no invented truth | cs-sparse-fresh |
| contradiction | settled point cased per settlement, open point registered | cs-contradiction-fresh |
| multi-domain | chained single-pack join, dual-domain blindness caught | cs-multidomain-fresh |
| stateful | two-run state transcript, env pinning | cs-stateful-fresh |
| nondeterminism | declared trial count, all-trials law, exhibited-trace anchor | cs-nondet-fresh |
| cost-pressure | witness per class inside budget, honest cost estimate | cs-cost-fresh |
| workflow-target | per-edge gates, frozen joins, HAZOP late + reverse | cs-workflow-fresh |
| ranking | required-failure excluded not ranked, declared ties, judge never re-executes | cs-ranking-fresh |
| intake-refusal | packet/synthesis deficiency blocks at intake, nothing invented | cs-intake-refusal |
| run-conduct | five stages, charter lanes, frozen joins, never-clauses in the run record | cs-run-conduct |
| package-audit | qualify-the-qualifier: identities, seven axes, independence, provenance grammar | cs-package-audit |

## Case package layout

`cases/<id>/` holds `case.toml` (the fourteen frozen schema keys),
`target/` (the artifact under test — a reference benchmark package,
or a reference blocked return for the negative rows), `evidence/`
(everything a builder may read, including the inner implementation
pool the package's own scoring is probed against), `probe/check.py`
(the case author's sanity oracle, NOT the benchmark), `seeds/good*/`
and `seeds/bad-<slug>/` (protected ground truth; each bad seed's
`defect.md` carries exactly one `deviation:` line naming deviation
and locus; exactly one inert variant and one near-miss per case),
and `expected.md` (criteria classes only — never transcribable
answers; each ends with the public canary footer).
`tools/validate_cases.py` is the normative schema statement.

## Protected evidence

Storage for the two held-back inputs (anti-goodhart workload class,
nondeterminism streams) is OFF-TREE, outside this sealed package,
fixed by sha256 in the manifest's `protected_evidence`. Probes read
`BENCH_PROTECTED_DIR` when set and degrade to public-subset checks
when unset, so the validator context is store-independent. The
candidate-inaccessible check is `null` at this seal: optimization
resistance is UNVERIFIED, an explicit gap. Two canary GUIDs
(public: expected.md footers; protected: store files) make verbatim
contamination detectable; nothing yet prevents it.

## Running the validator

    uv run --no-project python benchmarks/benchmaker/tools/validate_cases.py

Stdlib only. Exit 0 and silent when the set is clean; `--only`
drops the sixteen-row completeness check and never stands in for
the flagless run, which is the set's acceptance oracle.
