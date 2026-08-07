status: blocked
stage: evaluation design — materialization and qualification not started
reply_to: bench-caller-05

## Partial evidence

- codec-notes.md (sha256:50f04cf9a2c34d1a2203b836fc4c794ec45e8137f1d2da9ec43cc731ae4a2206) read in full; it is the
  only supplied material and is marketing prose: no interface
  specification, no sample streams, no transcripts, no measurement
  data.
- The intended outcome is perceived audio quality. The packet's
  judgment permission bars human listening and model-judged stand-ins;
  the source policy bars network, third-party decoders, corpora and
  metric implementations; the bitstream is opaque with no reference
  decoder. Every observation channel for the intended outcome is
  therefore barred or absent.
- The vendor makes no guarantee about any measurable property of the
  bitstream — size, timing, determinism — so no exhibited property of
  the encoder's output stands in for the outcome without substituting
  a different outcome.

## Gaps

- The intended outcome has no observation channel: human judgment is
  barred by the packet, and every objective comparison path requires a
  decoder, corpus, or metric the source policy bars.
- The sole evidence item exhibits no input, output, or trace; it
  licenses no anchor for any deterministic or judged check.
- Discrimination is UNVERIFIED for the whole target: with no channel,
  no known-bad variant can be shown to change the observable outcome.

## Unblock

Exactly one of, chosen by the caller — selecting among these fixes the
evaluation boundary, which is the caller's to fix:

- authorize a human listening channel and supply its protocol and
  results as evidence;
- supply a reference decoder together with a caller-authorized
  objective outcome defined over decoded output;
- name a different intended outcome that is observable under the
  current permissions.

## Spend

Evidence pass and evaluation design: 2 units of the small-tier
allocation. Materialization and qualification allocations returned
unspent; no benchmark identity was minted.
