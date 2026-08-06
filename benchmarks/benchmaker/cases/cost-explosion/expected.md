# What a qualified benchmark for globmatch must demonstrate

This case is the cost-pressure row of the matrix. It is passed when the
benchmark benchmaker produces discriminates across all four seeded
implementations *and* stays inside the declared bound. Either one alone
is a failed case: an exhaustive evaluation discriminates and busts the
bound, and a cheap random evaluation fits the bound and does not
discriminate. The case is only satisfiable by selecting the evaluation.

## Required

- **discrimination** — the benchmark passes `target/` and
  `seeds/good-tokenized/` and fails `seeds/bad-anchor/`,
  `seeds/bad-class-negation/` and `seeds/bad-range-upper/`. Failing to
  fail the near-miss is the expected way to lose this case.
- **cost-within-bound** — at most 2000 `match` calls and 5 s wall clock
  per candidate under `uv run --no-project python`, measured per
  implementation evaluated, not per suite.
- **reproducibility** — the target is a pure function; identical bytes
  must produce identical verdicts across runs.
- **schema-valid** — the manifest seals under
  `compositions/references/benchmaker-manifest.md`.

The second good seed exists to catch an evaluation that pins the
reference's implementation rather than the language: `good-tokenized`
compiles the pattern to a token list and scans forward with backtracking
instead of recursing with a memo table, and agrees with the reference on
all 893,101 pairs whose pattern and subject are four characters or
shorter.

## The bound is tight: the arithmetic

Take the pattern alphabet actually needed to express the language,
`a b c * ? [ ] ! -` (9 symbols), and subjects over `a b c` (3 symbols).
Truncate both to length `L` and enumerate:

| L | patterns | subjects | pairs | pairs / 2000 |
| --- | --- | --- | --- | --- |
| 2 | 91 | 13 | 1,183 | 0.6x |
| 3 | 820 | 40 | 32,800 | 16.4x |
| 4 | 7,381 | 121 | 893,101 | 446.6x |
| 5 | 66,430 | 364 | 24,180,520 | 12,090.3x |
| 6 | 597,871 | 1,093 | 653,473,003 | 326,736.5x |

Only `L = 2` fits the bound, and the shortest pattern that can express
a bracket set at all is three characters (`[a]`), a negated set four
(`[!a]`), a range five (`[a-c]`). So the one truncation that fits the
budget cannot express the construct that either interesting seed
depends on, and the smallest truncation that can witness the near-miss
costs 12,090x the bound. There is no truncation of this space that is
both affordable and sufficient — which is the whole point of the case.
Nor is enumeration merely truncated-expensive: pattern and subject
length are unbounded in the evidence, so the full space is infinite.

Sampling instead of enumerating does not rescue it. Witness densities,
each measured exhaustively over the smallest truncation that contains
any witness at all:

| seed | shortest witnessing pattern | witnesses | space | expected hits in 2000 uniform draws |
| --- | --- | --- | --- | --- |
| bad-anchor | 0 chars (`""` vs `"a"`) | 36 | 1,183 (L=2) | 60.9 |
| bad-class-negation | 4 chars (`[!a]`) | 27 | 893,101 (L=4) | 0.06 |
| bad-range-upper | 5 chars (`[a-c]`) | 18 | 24,180,520 (L=5) | 0.0015 |

A uniform draw finds the anchor bug immediately, the negation bug about
once in seventeen benchmark runs, and the near-miss about once in seven
hundred. Discrimination here is a property of choosing inputs, not of
spending them.

## The bound is satisfiable: the existence proof

`probe.py` — the case author's sanity oracle, not the benchmark — makes
50 `match` calls per implementation, 0.025x the bound, and separates the
reference and `good-tokenized` from all three bad seeds. A qualifying
benchmark therefore exists well inside the budget. benchmaker is not
asked to reproduce that table; it is asked to arrive at an evaluation
with the same two properties from the evidence alone.

## Expected gaps

None. The outcome is observable, the oracle is deterministic, and the
cost limit is stated in the evidence. A benchmark that declares a gap
here has misread the case.
