# Routing benchmark

Measures one thing: how often a fresh repository session routes a real user
prompt to the wrong lane. `cases.json` holds 30 prompts with the route each
should take — `answer`, `ticket`, `fix`, `build`, `named:<name>` — six of
them distractors borrowing a deleted or non-routed name whose route stays
`answer`/`ticket`/`fix`; `build` is expected only where the prompt names
`orch-build` (templates/host-block.md names everything else). It decides
SPEC §7.2 — all skill adapters on Claude, or the four both hosts expose —
each set installed into its own throwaway home (`--claude-adapters`).

    python tools/live_routing_bench.py --adapters both --repeat 3         --max-budget-usd 5 --out routing-bench.json

Opt-in and usage-consuming: one isolated live `claude` session per case,
set and repeat (the login must survive isolation; `--max-budget-usd` caps
spend). A pre-route failure grades `error`, outside the rate; final text
with nothing route-bearing is `answer`; a `by-name/<name>/SKILL.md` read is
`named:<name>`.

**Decision rule.** Four ships if its misroute rate ≤ all's + 0.05, over
repeats enough to beat the spread. **Verdict 2026-08-16** (results file):
all 0.500, four 0.633 — four fails; `all` stays. Decisive alone: named 5/5
vs 0/5 — under four no session used the by-name fallback. Caveat: the temp
repo is empty, so ticket/fix prompts naming repo files graded `answer` in
both sets (0/20); give the repo a fixture tree before re-measuring those.
