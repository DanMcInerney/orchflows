# Routing benchmark

Measures one thing: how often a fresh repository session routes a real
user prompt to the wrong lane. `cases.json` holds 30 prompts with the
route each should take — `answer`, `ticket`, `fix`, `build`, or
`named:<name>` — including six distractors that borrow a deleted or
non-routed name (`diagnose`, `triage`, `review`, `worklog`) while their
correct route stays `answer`/`ticket`/`fix`.

It exists to decide SPEC-ticket-set.md §7.2: whether Claude ships all
skill adapters or only the four both hosts expose. Each adapter set is
installed into its own throwaway home (`install.py --user
--claude-adapters all|four`), so only the host block routes.

    python tools/live_routing_bench.py --adapters both --repeat 3 \
        --out routing-bench.json

Opt-in and usage-consuming: it launches one live `claude` session per
case per adapter set per repeat. It measures and always exits 0 — it
never gates a suite. Each session runs under an isolated config dir, so
the CLI must be logged in through a mechanism that survives that
isolation (`claude setup-token`, or an API key in the environment); a
session that fails before routing grades `error`, never a route, and the
`errors` column must read 0 before the rates mean anything.

**Decision rule.** Four adapters ship if their misroute rate over this
case set is no more than the all-adapters rate plus 0.05; otherwise all
adapters stay. Run enough repeats that the gap is larger than the
run-to-run spread before reading it as a result.
