# What a qualified benchmark for this target must demonstrate

The target is a prompt (`target/summarize.md`). Its outcome is the
summary it produces, and that outcome is half byte-decidable and half
judged. This case exists to test whether BenchMaker builds a benchmark
that keeps the two halves apart and ranks them correctly.

## 1. The deterministic half, held by the benchmark

Three checks, each failable, each reproducible without a judge:

- every citation token resolves to an id declared in
  `evidence/sources.md`;
- the prose is within 120 words, headings and citation tokens excluded;
- every sentence of the body carries at least one citation.

The bound and the citation policy are the case's, not the candidate's. A
benchmark that reads `max_words` out of the prompt under test and scores
against that number is not qualified: `seeds/bad-over-length/` passes
such a benchmark by declaring `max_words: 400` and then obeying itself.

## 2. The judged half, anchored

Three criteria. Each carries a stated scale with a worked anchor at each
level, drawn from artifacts in this case so a second judge can calibrate
against the same bytes.

**Faithfulness — does the claim match what the cited source says?**

- 2 holds: every sentence's claim is stated by the source it names.
  Anchor: `target/output.md`, "p99 read latency fell from 412 ms to
  96 ms after full enablement [S2]" — `S2` states exactly this.
- 1 drifts: the cited source is topical but the claim is broader than
  what it states. Anchor: a sentence citing `S4` for a claim that the
  rollout "paid for itself", where `S4` gives two figures and no verdict.
- 0 fails: the citation names an id the source set does not declare, or
  attaches a claim its named source never makes. Anchor:
  `seeds/bad-fabricated-citation/output.md`, "The rollback runbook was
  followed exactly as written during the flush [S7]".

**Coverage — is the unflattering half still present?**

- 2 holds: the digest carries both the rollout outcome (latency, cost)
  and the incident. Anchor: `seeds/good-terse/output.md`, four sentences
  carrying `S1`–`S5` between them.
- 1 partial: the incident appears but its open follow-up is dropped.
- 0 fails: the digest reports only the rollout's wins.

**Restraint — does it add what no source states?**

- 2 holds: no recommendation, cause, or figure beyond the set.
- 1 drifts: a causal connective the sources do not draw.
- 0 fails: a recommendation or a number no source carries. Anchor:
  `seeds/bad-uncited-claims/output.md`, "The rollout was on the whole
  the smoothest of the quarter" — a verdict no source supports.

**Secondary, and stated as such.** A candidate failing any deterministic
check is not rescued by a judged score. `seeds/bad-over-length/` is the
test of this rule: it is the most faithful and most complete of the four
variants on the judged criteria and must still be scored a failure,
because it is twice the bound. A benchmark whose aggregate lets
faithfulness compensate for a length failure is not qualified.

## 3. Discrimination, seed by seed

The produced benchmark must separate the reference and
`seeds/good-terse/` from each bad seed, and must do so through the
criterion that owns the defect rather than by accident:

| seed | must be caught by | not by |
| --- | --- | --- |
| bad-fabricated-citation | citation resolution against the closed set; faithfulness 0 | word count |
| bad-over-length | the case's own 120-word bound | any bound read from the candidate |
| bad-uncited-claims | per-sentence citation coverage; restraint 0 | citation resolution or word count — both pass |

`bad-uncited-claims` is the near-miss and the discrimination test that
matters. It passes the two checks a benchmark reaches for first and
fails only the third, so a benchmark that quantifies over citations
("is every citation valid?") scores it clean while a benchmark that
quantifies over sentences ("does every sentence have an owner?") catches
it. Both benchmarks look reasonable in a design review; only one has
discrimination. Qualification must exhibit the failing run, not assert
the capability.

## 4. Qualification verdicts expected

`case.toml`'s `expected_qualification` names the enum values; they mean:

- **discrimination** — reference and good seed pass, all three bad seeds
  fail, each through its own criterion per the table above, and the
  judged anchors above are present with a worked example at each level.
  Anchorless judged criteria ("rate faithfulness 1-5") fail this.
- **reproducibility** — the deterministic checks recompute identically
  from the same bytes; the judged pass is re-runnable against fixed
  anchors and its variance is recorded.
- **schema-valid** — the benchmark seals under the manifest schema with
  every component fixed by identity.
- **cost-within-bound** — the run stays inside `case.toml`'s `bound`.

## 5. The probe is not the benchmark

`probe.py` is the case author's sanity oracle. It covers
only the deterministic half — it has no opinion on faithfulness,
coverage, or restraint, and it reads a fixture output rather than
running the prompt, so the case stays offline. Its passing on the
reference and failing on every bad seed is evidence that the seeds are
real and distinct, not evidence that a benchmark exists.
