# Three-stage pipeline — specification

The inner target is a declarative pipeline description,
`pipeline.json`, executed by the deterministic interpreter shipped
beside this spec (`interpreter.py`). The canonical pipeline is

    spec -> build -> verify

## Description format

A JSON object:

- `stages`: list of `{id, consumes, produces}`. `consumes` is a list
  of artifact names (optional). `produces` is optional:
  `{artifact, payload, freeze}` — `freeze` true records the artifact's
  identity at production and makes it immutable; `freeze` false leaves
  it live.
- `edges`: list of `{from, to, gate}`. `gate` is the gate's name; an
  edge whose `gate` is null or absent is ungated.
- `run`: the execution order, a list of stage ids.

## Gate law (per-edge)

Every edge of the canonical graph must carry a gate, and the gate must
pass between the upstream stage's completion and the downstream
stage's work. An ungated edge — including the last one — is a
violation.

## Join-identity law

A consuming stage must consume exactly the frozen identity the
producing stage recorded. Consuming a live (unfrozen) artifact, an
artifact that does not exist yet, or bytes whose identity differs from
the frozen record is a violation. (The interpreter models live-artifact
drift: an unfrozen artifact's payload mutates deterministically at
every subsequent stage boundary.)

## Stage-order law

For every edge `S -> T`, stage `S` completes before stage `T` starts.

## Transcript grammar

The interpreter emits one line per event, in execution order:

    STAGE-START <stage>
    GATE <name> <from>-><to> PASS
    JOIN <stage> CONSUMES <artifact> <sha256-hex|MISSING>
    ARTIFACT <artifact> FROZEN|LIVE <sha256-hex>
    STAGE-END <stage>

Within a stage the order is: gates, joins, artifact, end. A benchmark
package for this target scores transcripts against the three laws
above plus an aggregate gate: an empty run never passes.

## Package interface

A benchmark package for this target exposes these fixed paths,
whatever its manifest locators say (the manifest and qualification
record shapes are in `interchange.md` beside this spec):

    runner/run.py
    runner/check_transcript.py
    provenance/events.md
    provenance/evaluation-design.md
    qualification/qualification.json

Command lines:

- `python runner/run.py <impl-dir> --interpreter <interpreter.py>` —
  runs one implementation's pipeline through the supplied interpreter
  and scores it; the exit code is the verdict (0 pass, nonzero fail).
- `python runner/check_transcript.py <transcript-file>` — scores one
  already-emitted transcript; exit 0 accepts, nonzero rejects. An
  empty transcript is rejected.

Seal ledger: `provenance/events.md` records the seal events one per
line, containing these three tokens in this order — an event may not
appear later than one it must precede:

    components-frozen
    qualification-recorded
    identity-minted

Design-evidence flow: `provenance/evaluation-design.md` names each of
its inputs on its own line of the form

    evidence-source: case-evidence:pipeline-spec.md

Evidence sources never name the package's own downstream components
(`cases/`, `runner/`, `scoring/`, `qualification/`).

Qualification coverage: each qualification entry's `covers` is an
object mapping component names to that component's recorded identity,
for example

    "covers": {"runner": "sha256:<hex>", "scoring": "sha256:<hex>"}

Every `covers` value must be a component identity of this package;
none may be the package's own `benchmark_identity`.
