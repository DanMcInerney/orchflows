# Routing benchmark

Measures one thing: how often a fresh repository session routes a real user
prompt to the wrong lane. `cases.json` holds 30 prompts with the route each
should take — `answer`, `ticket`, `fix`, `build`, `named:<name>` — six of
them distractors borrowing a deleted or non-routed name (`diagnose`,
`triage`, `review`, `worklog`) whose route stays `answer`/`ticket`/`fix`.
`build` is expected only where the prompt names `orch-build`, because
templates/host-block.md routes an unnamed request to answer, ticket or fix
and names everything else. It decides SPEC-ticket-set.md §7.2 — all skill
adapters on Claude, or the four both hosts expose — each set installed by
`install.py --user --claude-adapters all|four` into its own throwaway home.

    python tools/live_routing_bench.py --adapters both --repeat 3 \
        --max-budget-usd 5 --out routing-bench.json

Opt-in and usage-consuming: one isolated live `claude` session per case, set
and repeat, so the CLI's login must survive that. `--max-budget-usd` stops
launching once the summed cost passes it. A session failing before it routes
— API error, timeout — grades `error`, outside the rate: misroutes over the
sessions that ran. An answer is a final text with nothing route-bearing
before it; a read of `by-name/<name>/SKILL.md` is the route `named:<name>`.

**Decision rule.** Four adapters ship if their misroute rate is no more than
the all-adapters rate plus 0.05, over repeats enough to beat the spread.
