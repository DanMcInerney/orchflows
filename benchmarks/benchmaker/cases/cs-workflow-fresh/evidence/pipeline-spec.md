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
