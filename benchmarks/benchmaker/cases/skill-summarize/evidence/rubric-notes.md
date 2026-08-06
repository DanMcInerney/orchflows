# Which half is judged

Notes for whoever builds the benchmark for this target. They record
where the deterministic/judged line falls; they do not prescribe the
benchmark's design.

## Deterministic half

Word bound, closed citation set, citation coverage. Each is a byte-level
predicate over the produced summary, each fails loudly, and each is
reproducible without a model in the loop.

## Judged half

- **Faithfulness.** Does the claim match what the cited source says? A
  summary can cite `[S4]` on a latency claim: the id resolves, the
  sentence is cited, and the attribution is still wrong.
- **Coverage.** Does the summary carry both the outcome (latency and
  cost) and the incident, or has it dropped the unflattering half?
- **Restraint.** Does it add a recommendation, a cause, or a number no
  source states?

These need anchors — a stated scale with a worked example at each end —
because a bare "rate faithfulness 1–5" is not reproducible across
judges. Anchors are the judged half's substitute for a byte predicate.

## Ordering

The judged half is secondary: it cannot rescue a summary that failed the
deterministic half, and a high faithfulness score over an over-length,
uncited summary is not a pass. See
`compositions/references/benchmaker-protocol.md`, qualification: judged
criteria carry anchors, remain secondary, and cannot compensate for
required deterministic failure.
