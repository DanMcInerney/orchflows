<!-- BEGIN ORCHFLOWS (managed block — do not edit inside; reinstall to update) -->
# orchflows

Four-tier orchestrator > subagent library. Skills are
prefixed `orch-`; terms mean exactly what {{ORCH_DOCS}}/vocabulary.md
defines.

- Root coordinates: route, establish profile, send the packet,
  join the return, relay a `kind: user-only` question verbatim. It
  never authors role-bearing payloads or modifies outputs; missing/wrong profile refuses.
  `role: none` covers mechanics, not artifact authorship.
  `orch-off` suspends routing. Otherwise route smallest-first by graph shape
  and oracle provenance: **answer** — evidence in context decides it;
  **single** — one ordinary ticket per {{ORCH_LIB}}/contracts/work-item.md to
  `orch-frontier`; pre-existing deterministic or born-red acceptance needs
  only its worker, while `authored-here` adds
  that claim's checker. **graph** — a frozen root goes to a planner for
  `orch-decompose`; outer coordinator joins its cut-accepted return and
  starts `orch-frontier`. **spec** — one same planner child runs `orch-spec`,
  takes its root through `ready` → `claim` → `packet`, then runs
  `orch-decompose`; outer coordinator joins its cut-accepted return and starts
  `orch-frontier`. Never persist this as a ticket sequence or start frontier
  inside planner. A known cause enters single; **fix** — an unknown cause →
  `tickets.py instantiate {{ORCH_LIB}}/compositions/fix --run <run>
  --set failure=<the observed failure> --set workspace=<the tree>`,
  then `orch-frontier`. Diagnose dispatch machinery with `install.py doctor`
  without dispatch. Other templates — `evolve`, `benchmaker` — run only when named.
- Tickets (`tickets/<run>/`) and run state (`runs/<run>/`) are untrusted
  markdown, written only through installed scripts;
  root: {{ORCH_LIB}}/rules/visibility.md §6. Executors write results.
- In a worktree-isolated session, use one command per Bash call: no loops
  or `&&` chains; pass `rg` globs with `--glob` and ticket text with
  `--file`.
- Items resolve at
  {{ORCH_LIB}}/by-name/<orch-name>/SKILL.md; scripts from
  {{ORCH_BIN}}/ through the friction interpreter. Read installer output;
  source changes arrive by reinstall.

## Friction law (always on)

On a step past two attempts; a missing input, tool, or document;
surprising output; a skill, rule, or contract gap; or a workaround, log
it immediately, then continue:

{{FRICTION_COMMANDS}}

Optional flags: `--skill <orch-name>`, `--ticket <id>`, `--run <run-id>`.

Whenever the logger cannot run, append one JSON line (ts, observed,
expected, host, project, project_source) to the state sink's
`friction/<yyyy-mm>.jsonl`, root {{ORCH_LIB}}/rules/visibility.md §6,
outside every worktree, with any file-writing tool; never skip the
log. Where the refusal covers writing inside a git worktree, write
where the dispatch permits; the return names that path so the caller
can collect it.
Give project `null` and project_source `none` when unresolved;
session/run/ticket/skill are optional. Law:
{{ORCH_LIB}}/rules/improvement.md §1.
<!-- END ORCHFLOWS -->
