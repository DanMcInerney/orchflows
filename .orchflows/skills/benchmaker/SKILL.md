---
name: benchmaker
description: Construct and qualify one runnable benchmark suite from a declared target and intended outcome.
role: none
---

Require: a request whose spec `objective` names one target identity and
intended outcome; `routing` names one target pack; `evidence` names access,
target-pack references, and an admitted T0 carrier whose contract supplies a
frozen research synthesis to an existing orch-bench Require field; `bound`
names one execution budget; and `binding_constraints` names judgment
permission.

Read [references/protocol.md](references/protocol.md) once at open. If
`evidence` does not name the admitted carrier, fail closed before work and
return partial evidence with a `decision_gap`.

Execute only this order:

1. Through `orch-spec`, freeze the research spec and its bound allocation.
2. Through `orch-deliver`, deliver the frozen research spec.
3. If research is non-complete, has a `decision_gap`, or leaves a remainder,
   return partial evidence; do not design.
4. Through the admitted carrier, call `orch-bench` with the frozen synthesis.
5. If the design is invalid or UNVERIFIED, return partial evidence; do not
   construct.
6. Through the same spec owner, freeze the construction spec from the exact
   frozen synthesis and bench.
7. Through the same delivery owner, deliver the construction spec and return.

Never: improve or mutate the target; design criteria, oracles, anchors,
weights, aggregation, a loss check, or a generation brief outside the bench
owner; alter the frozen task set during pack slicing; multiply the caller's
bound; let a case builder qualify its own oracle.

Return: the runnable suite, execution instructions, coverage map, research
provenance, qualification verdicts and expected cost, and explicit gaps; on
failure, the same fields populated by partial evidence, with `decision_gap`
and uncovered remainder carried in explicit gaps (`[]` when none).
