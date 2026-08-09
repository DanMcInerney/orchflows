deviation: oracle-vacuity @ limiter scoring

Inert variant: the intended behavior — discriminating scoring — is
absent entirely. `scoring/score.py` reports PASS for every
implementation without executing a single case; the runner and case set
are shipped but never consulted. Everything else is lawful — every
component locator resolves, including the changed scoring component.

Burn note: `oracle-vacuity` is a census name; its predecessor burn was
at the composition-target package oracle. This locus — the limiter
scoring script — is fresh.
