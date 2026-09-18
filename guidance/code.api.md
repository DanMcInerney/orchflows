# API code

Prefer stable caller contracts and machine-readable errors. Make ordering and pagination limits explicit; state whether repeating a request repeats its effect. Distinguish absent, empty and invalid values when their behavior differs.

## Review

Check whether a caller can recover from errors and retry without guessing. Flag accidental contract changes and ambiguous behavior at the interface's limits.
