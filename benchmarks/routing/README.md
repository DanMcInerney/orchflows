# Routing benchmark

Measures how often a fresh repository session routes a real user prompt to the
wrong lane. `cases.json` holds 38 prompts routed to `answer`, `single`, `graph`,
`spec`, `fix`, `build`, or `named:<name>`; six are distractors. `build` requires
naming `orch-build`. It decides SPEC §7.2: all
Claude skill adapters, or the four both hosts expose, installed into separate
throwaway homes (`--claude-adapters`).

The 2026-08-25 Codex-catalog counterfactual pairs an `answer` for explanation
with one known-cause `single` ticket containing all coupled and derived
consequences; it uses no spec, decompose, or fix workflow.

    python tools/live_routing_bench.py --adapters both --repeat 3         --max-budget-usd 5 --out routing-bench.json

Opt-in and usage-consuming: one isolated live `claude` session per case, set,
and repeat (login must survive isolation; `--max-budget-usd` caps spend). A
pre-route failure grades `error`, outside the rate; final text with nothing
route-bearing is `answer`; a `by-name/<name>/SKILL.md` read is `named:<name>`.
A direct role-bearing case matches only one exact role/skill child, none at root.

**Decision rule.** Four ships if its misroute rate ≤ all's + 0.05 over enough repeats. **Verdict 2026-08-16** (results file):
all 0.500, four 0.633 — four fails; `all` stays. Decisive alone: named 5/5
vs 0/5 — under four no session used the by-name fallback. The empty temp repo
made ticket/fix file prompts grade `answer` in both sets (0/20).
