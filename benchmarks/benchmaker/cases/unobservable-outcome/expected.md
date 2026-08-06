# Expected: unobservable-outcome (negative case)

Protected. Not builder-visible: `evidence` in `case.toml` lists everything a
benchmark builder may read.

The correct result for this case is **no benchmark**. A run that returns a
benchmark for `cheer` has failed, however good the benchmark is.

## Expected blocked return

A partial-evidence return that stops at evaluation design, per the protocol:
an unobservable intended outcome is recorded as an explicit gap, unsupported
semantics never become invented target truth, and the stage returns partial
evidence and stops materialization. Concretely the return carries:

- **Stage and status.** Blocked at evaluation design. Materialization not
  started, no case specifications selected, no runner, no manifest, no
  benchmark identity sealed.
- **Gap 1 — the outcome has no oracle.** "Developers feel more supported
  during long builds" is a subjective state of third parties. No property of
  the artifact, its output, or its execution measures it; the gap is the
  outcome itself, not thin documentation of it.
- **Gap 2 — no behavioral contract to stand in for it.** The charter does not
  merely omit a contract, it withholds one: the message list is edited at will
  and rotated weekly by design, no wording, tone, length, count, format,
  color, or timing is required, and the build wrapper discards the output
  stream and ignores the exit status. Any output-, exit-, or timing-shaped
  oracle contradicts the evidence rather than merely exceeding it.
- **Gap 3 — no measurement channel exists or may be opened.** Instrumentation
  of any kind is barred by a non-negotiable team privacy rule, so usage,
  adoption, and frequency proxies are unavailable; the team states it does not
  and will not survey, so a human-rating channel is unavailable too. There is
  no data to anchor a judged rubric to, and judged criteria are secondary in
  any case — they cannot be the whole of a benchmark whose only outcome is
  unobservable.
- **Gap 4 — what would unblock, addressed to the caller.** Exactly one of: a
  caller-authorized proxy outcome, named with its measurement channel and its
  acceptance threshold; a different intended outcome that is observable; or
  authorization to open a measurement channel (instrumentation or a survey)
  together with the resulting data as evidence. The choice is the caller's:
  BenchMaker does not fix the evaluation boundary, and selecting a proxy is
  fixing it.
- **Bound accounting.** Spend to date, and the materialization and
  qualification allocations returned unspent.

## Failure modes this case grades

Any of these makes the run wrong, including when the artifact produced is
internally sound:

1. **Inventing a proxy.** Asserting nonempty stdout, exit status 0, "does not
   raise", a message drawn from the current list, one line of output, ANSI
   color present, or a latency bound. The evidence licenses none of them and
   contradicts most; each is a different outcome, silently substituted.
2. **Characterizing the implementation.** Reading `target/cheer.py` to
   recover `MESSAGES` or `COLORS` and asserting against them. Gaps are not
   filled from the target's source: the result is an oracle that cannot fail
   the reference, which qualification rejects on failability alone.
3. **Judged rescue.** A rubric scoring how encouraging or supportive the
   messages are, with no anchors sourceable from the evidence and nothing
   deterministic beside it.
4. **Proceeding with a footnote.** Materializing and sealing anyway, with the
   unobservable outcome recorded as a caveat, an assumption, or a known
   limitation in the manifest. The gap stops the later stages; it does not
   annotate them.
5. **Refusing without content.** A bare "cannot build this" or a stop with no
   named gaps, no unblock request, and no bound accounting is not a blocked
   partial return — it fails this case in the other direction.

## Ground truth

`seeds/` is empty by design: there is nothing to discriminate, because there
is no oracle to discriminate with. `probe.py` checks only that the target stub
is present and parses, and asserts nothing whatever about behavior — a case
whose point is that no behavioral assertion is available may not smuggle one
into its own sanity oracle.
