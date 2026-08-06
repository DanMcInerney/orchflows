# What a qualified benchmark for `scaffold.py` must demonstrate

The target emits two artifacts from one input: a module other programs call
and a document people read. A benchmark that grades one of them is not a
benchmark of this target.

## Both halves, each with its own oracle class

| half | artifact | oracle class | what it must do |
| --- | --- | --- | --- |
| code | `validate_<record>.py` | deterministic | import the generated module and execute `validate` against a record matrix; compare error lists exactly, in field order, including a record with two independent violations |
| report | `REPORT.md` | judged or structural | check the field table against the schema and check the advertised message list against the messages the generated module demonstrably emits |

The report half may be scored structurally (parse the table and the bullet
list) or by a judge against anchors. If it is judged, the judged criteria stay
secondary: a required deterministic failure on the code half blocks
qualification and no report score compensates for it. Judged anchors must
name the coupling — the report's claims are graded against the same run's
generated module, never against plausibility alone.

## Materialization

Because the cases span a code domain and a document domain, the benchmark is
materialized as chained single-pack runs through frozen evidence identities,
not one mixed run: one code-pack run owns the deterministic half, one
content-pack run owns the report half, and the shared schema plus the
generated artifacts cross the chain by identity. A single mixed run is a
protocol violation even when it happens to produce both oracles.

## Discrimination

The benchmark must pass `target/scaffold.py` and `seeds/good-variant/`, and
fail all three bad seeds. The good variant restructures the generator and
rewords the report prose without changing behaviour: a benchmark that matches
source text or report wording fails a good seed, which is itself a benchmark
defect.

### Which seed a single-domain benchmark provably misses

| benchmark that grades | scores as good, wrongly |
| --- | --- |
| the code half only | `bad-lying-report`, `bad-stale-error-list` |
| the report half only | `bad-broken-code` |

`bad-broken-code` is the decisive one for the doc-only direction: its report
is fully accurate — correct table, and every advertised message really is
emitted for some record — so no amount of report scrutiny reaches the early
return that hides the second violation. `bad-stale-error-list` is the
near-miss: it survives both a code-only benchmark and any report check that
stops at field coverage, and falls only to a check that compares the report's
message list against the module's actual output.

## Reproducibility and cost

The target reads one JSON file and writes two files; there is no clock, no
network, no randomness, and no state carried between runs. Two runs from the
same schema must produce byte-identical artifacts. Generation plus both halves
must stay inside the case bound; a benchmark that enumerates schemas
combinatorially is over cost for no discrimination gain.

## Out of scope

Prose quality of the report beyond `evidence/report-contract.md`; the schema
document's own validation; performance.
