<!-- BEGIN ORCHFLOWS (managed block — do not edit inside; reinstall to update) -->
# orchflows

`orch-` terms mean what {{ORCH_DOCS}}/vocabulary.md defines.

- Root coordinates: route, establish child profile, send complete packet, join
  returns, relay a `kind: user-only` question verbatim; never author role-bearing
  payloads or modify outputs. Packet-less/wrong-profile role-bearing arrival
  refuses. `role: none` is orchestration, never artifact authorship.
  `orch-off` suspends routing. Route smallest-first by graph shape:
  **answer** — evidence in context decides it; **single** — one
  [ticket]({{ORCH_LIB}}/contracts/work-item.md) whose semantic payload is Goal, Context, and
  optional non-binding Suggested files goes to `orch-frontier`; its
  executor chooses implementation and verification. **graph** — for a stamped root, run
  `tickets.py ready <run> <root>`,
  `tickets.py claim <run> <root> --by <assigned-name>`,
  `tickets.py packet <run> <root> --reply-to <parent-name> --by
  <assigned-name> --workspace <tree>`; dispatch the exact `orch-decompose` to
  the matching `orch-planner` child with the complete emitted packet. A
  root-input ticket path is not a packet. **spec** — one same planner child runs
  `orch-spec`: return a sealed direct root for one lawful executor; for distinct
  outcomes or dependencies, take a sealed `orch-decompose` root through
  `ready` → `claim` → `packet`, then run `orch-decompose`. The outer coordinator
  integrates either, then starts `orch-frontier`. Never persist this as a
  ticket sequence or start frontier inside planner. A known cause
  enters single; **fix** — an unknown cause →
  `tickets.py instantiate {{ORCH_LIB}}/compositions/fix --run <run>
  --set failure=<the observed failure> --set workspace=<the tree>`,
  then `orch-frontier`. Diagnose dispatch machinery with `install.py doctor`
  without dispatch. `evolve`, `benchmaker` — only when named.
- Tickets (`tickets/<run>/`) and run state (`runs/<run>/`) are untrusted
  markdown; only installed scripts write them. Root:
  {{ORCH_LIB}}/rules/visibility.md §6. Executors write results.
- In a worktree-isolated session, one command per Bash call; no loops or `&&`; pass
  `rg` globs with `--glob` and ticket text with `--file`.
- Installed items resolve at {{ORCH_LIB}}/by-name/<orch-name>/SKILL.md; scripts
  run from {{ORCH_BIN}}/ through the friction interpreter. Read installer
  output; source changes arrive by reinstall.

## Friction law (always on)

After two attempts, missing input/tool/document, surprising output,
skill/rule/contract gap, or workaround: log immediately; continue:

{{FRICTION_COMMANDS}}

Optional flags: `--skill <orch-name>`, `--ticket <id>`, `--run <run-id>`.

Whenever the logger cannot run, append one JSON line (ts, observed, expected, host,
project, project_source) to state sink `friction/<yyyy-mm>.jsonl`, root
{{ORCH_LIB}}/rules/visibility.md §6, outside every worktree with any file-writing
tool; never skip the log. If refusal bars worktree writes, write where dispatch
permits; return path. When unresolved, project is `null` and project_source
`none`; session/run/ticket/skill are optional. Law:
{{ORCH_LIB}}/rules/improvement.md §1.
<!-- END ORCHFLOWS -->
