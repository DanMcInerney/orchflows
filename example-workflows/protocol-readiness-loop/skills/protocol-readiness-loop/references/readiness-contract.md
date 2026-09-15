# Readiness contract

## Accepted-finding closure

An accepted or modified finding is incomplete until its change map traces this semantic closure in order:

`state -> rule -> schema -> serialization -> receipt -> failure mapping -> terminal result -> verification fixture`

For each node, record the owning location and intended change, or the literal `INAPPLICABLE` plus a reason. The adjudicator checks the whole chain even when the observed defect looks local. An updater may not collapse downstream nodes into a generic "aligned elsewhere" statement.

## Stable failure-class identity

A failure class is a durable identifier backed by three properties:

1. the invariant that should hold;
2. the observable way it failed;
3. the semantic or execution boundary where the failure becomes consequential.

Record those properties and cited evidence with the class. A later finding is the same class only when an adjudicator confirms all three properties and records `same_as` with the prior class identifier. Shared wording, file location or proposed remedy is not proof of identity. Splits and merges receive new identifiers with explicit lineage.

Ordinary prose repair stops when one evidenced class is present after each of two completed revisions intended to close it. Count revisions, not rewordings or verifier retries. The terminal status is `BLOCKED`, reason `RECURRENT_FAILURE_CLASS`; the reason names the class, the two revision identities and the evidence supporting continuity.

## Mechanizability gate

Stop artifact-only repair when correctness depends on exact bytes, ordering, state transitions, serialization, retry behavior or similarly executable semantics and the adjudicator cannot settle the requirement reliably from artifacts alone. Use top-level `BLOCKED` with reason `MECHANISM_PROBE_REQUIRED`.

Return a bounded probe brief containing the disputed invariant, fixed inputs, observable oracle, allowed operations, resource bound, expected evidence and later-readiness re-entry condition. The readiness loop must not implement or run the probe. A probe requires separate authorization and returns frozen evidence to a later readiness cycle; its result does not resume or extend the stopped cycle automatically.

## Conformance repair allowance

The caller may set a nonnegative per-revision repair limit; default 2. The first conformance check is not a repair attempt. Each updater action after a failed conformance check consumes one attempt, whether or not the next check passes. Preserve every failed candidate, map and verdict. If the final allowed repair still fails, stop `BLOCKED` with reason `CONFORMANCE_REPAIR_LIMIT_REACHED`; never borrow from the round limit or silently extend either bound.

## Status compatibility

The top-level terminal vocabulary is closed and backward compatible:

`READY_FOR_OWNER_FREEZE | OWNER_DECISION_REQUIRED | ROUND_LIMIT_REACHED | BLOCKED | INVALID`

`MECHANISM_PROBE_REQUIRED`, `RECURRENT_FAILURE_CLASS` and `CONFORMANCE_REPAIR_LIMIT_REACHED` are reason codes under `BLOCKED`, never top-level statuses. Existing consumers can continue parsing the terminal status. Consumers that route work should also inspect the structured reason and next action.
