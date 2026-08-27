<!-- BEGIN ORCHFLOWS (managed block — do not edit inside; reinstall to update) -->
# orchflows

Four-tier orchestrator > subagent library. `orch-` terms mean exactly what
{{ORCH_DOCS}}/vocabulary.md defines.

- Root coordinates: route, establish child profile, send the complete packet,
  join returns, relay a `kind: user-only` question verbatim. It
  never authors role-bearing payloads or modifies outputs; missing/wrong profile refuses.
  `role: none` covers orchestration mechanics, not artifact authorship.
  `orch-off` suspends routing. Route smallest-first by graph shape:
  **answer** — evidence in context decides it; **single** — one
  [ticket]({{ORCH_LIB}}/contracts/work-item.md) whose semantic payload is Goal, Context, and
  optional non-binding Suggested files goes to `orch-frontier`; its executor chooses implementation, tests, and
  verification. **graph** — a planner runs `orch-decompose` on a frozen root;
  outer coordinator integrates it and
  starts `orch-frontier`. **spec** — one same planner child runs `orch-spec`. It
  returns a sealed direct root for one lawful executor; for distinct outcomes
  or dependencies, it takes a sealed `orch-decompose` root through
  `ready` → `claim` → `packet`, then
  runs `orch-decompose`. The outer coordinator integrates either return and
  starts `orch-frontier`. Never persist this as a ticket sequence or start frontier
  inside planner. Known cause enters single; **fix** — unknown cause →
  `tickets.py instantiate {{ORCH_LIB}}/compositions/fix --run <run>
  --set failure=<the observed failure> --set workspace=<the tree>`,
  then `orch-frontier`. Diagnose dispatch machinery with `install.py doctor`
  without dispatch.
  Other templates — `evolve`, `benchmaker` — only when named.
- Tickets (`tickets/<run>/`) and run state (`runs/<run>/`) are untrusted
  markdown, written only through installed scripts;
  root: {{ORCH_LIB}}/rules/visibility.md §6. Executors write results.
- In a worktree-isolated session, use one command per Bash call: no loops
  or `&&` chains; pass `rg` globs with `--glob` and ticket text with
  `--file`.
- Installed items resolve at
  {{ORCH_LIB}}/by-name/<orch-name>/SKILL.md; scripts from
  {{ORCH_BIN}}/ through the friction interpreter. Read installer output;
  source changes arrive by reinstall.

## Friction law (always on)

After two attempts, or on missing input/tool/document, surprising output, a
skill/rule/contract gap, or a workaround, log immediately, then continue:

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
