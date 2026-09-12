# API code

## Make

Design the contract from the caller's perspective: inputs, outputs, authentication, errors and compatibility. Validate at the trust boundary and keep error responses stable and useful without exposing internals. Distinguish absent, empty and invalid values where they mean different things.

Make retries and partial failure explicit. For mutations, decide whether repeated requests may repeat effects; for collections, define ordering, pagination and limits. Change published contracts deliberately, with a migration path when existing clients would break. Keep examples executable against the actual interface.

## Review

Exercise a representative caller against the contract, including unauthorized, malformed, duplicate and boundary requests. Check that behavior matches documentation and that a client can recover from errors without guessing. Look for accidental breaking changes, inconsistent validation, unbounded operations and retry paths that duplicate effects.
