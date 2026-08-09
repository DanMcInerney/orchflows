deviation: oracle-vacuity @ query scoring

Inert variant: the intended behavior — discriminating scoring — is
absent entirely. `scoring/score.py` reports PASS for every
implementation without evaluating a single query; the runner, case set,
and corpus parameters are shipped but never consulted. Everything else
is lawful — every component locator resolves, including the changed
scoring component.

Burn note: `oracle-vacuity` is a census name; its predecessor burn was
at the composition-target package oracle. This locus — the log-query
scoring script — is fresh.
