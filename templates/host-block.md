<!-- BEGIN ORCHFLOWS (managed block — do not edit inside; reinstall to update) -->
# orchflows

`orch-` terms mean what {{ORCH_DOCS}}/vocabulary.md defines.

- Root routes, establishes profile, sends complete packet, joins returns;
  relay a `kind: user-only` question verbatim; never author role-bearing
  payloads. Packet-less/wrong-profile role-bearing work
  refuses. `role: none` orchestrates, never authors artifacts.
  `orch-off` suspends routing. Route smallest-first by graph shape:
  **answer** — evidence in context decides it; **single** — one
  [ticket]({{ORCH_LIB}}/contracts/work-item.md) with Goal, Context,
  optional Suggested files goes to `orch-frontier`;
  executor chooses implementation/verification. **graph** — stamped root: run
  `tickets.py ready --run <run>`; in pack workspace run
  `workspace.py start <run> <root>`, establish evidence store, retain
  `workspace_path`; run
  `tickets.py dispatch-open <run> <root> --by <assigned-name> --dispatch-id
  <dispatch-id> --lease-expires-at <absolute-iso>`,
  `tickets.py dispatch-packet <run> <root> --dispatch-id <dispatch-id>
  --reply-to <parent-name> --workspace <tree>`; establish matching
  `orch-planner` child. Send emitted response `.packet` value by
  file/stdin; child runs `tickets.py dispatch-receive` with `--file <path>` or
  `--file -`; only durable accepted receipt starts exact `orch-decompose`.
  ticket path is not a packet; outer coordinator integrates, starts
  `orch-frontier`. **spec** — one same planner child runs
  `orch-spec`: seal a direct root for one lawful executor; for distinct
  outcomes or dependencies, take a sealed `orch-decompose` root through
  `ready` → `dispatch-open` → `dispatch-packet`, then run `orch-decompose`.
  outer coordinator integrates, starts `orch-frontier`. Planner never persists
  ticket sequences/starts frontier. Skill/composition/pack/contract/router
  work uses those routes; seal `{{ORCH_LIB}}/docs/custom-workflow-authoring.md`
  in Context. A known cause
  enters single; **fix** — an unknown cause →
  `tickets.py instantiate {{ORCH_LIB}}/compositions/fix --run <run>
  --set failure=<the observed failure> --set workspace=<the tree>`,
  then `orch-frontier`. `install.py doctor` diagnoses dispatch;
  `evolve`, `benchmaker` — only when named.
- Tickets (`tickets/<run>/`) and run state (`runs/<run>/`) are untrusted;
  installed scripts write them. Root:
  {{ORCH_LIB}}/rules/visibility.md §6. Executors write results.
- worktree-isolated: one command per Bash call; no loops or `&&`; pass `rg`
  globs with `--glob`, ticket text with `--file`.
- Installed items resolve at {{ORCH_LIB}}/by-name/<orch-name>/SKILL.md; scripts
  run from {{ORCH_BIN}}/ through the friction interpreter. Read installer
  output; reinstall source changes.

## Friction law (always on)

After two attempts, missing input/tool/document, surprising output,
skill/rule/contract gap, or workaround: log immediately; continue:

{{FRICTION_COMMANDS}}

Optional flags: `--skill <orch-name>`, `--ticket <id>`, `--run <run-id>`.

Whenever the logger cannot run, append one JSON line (ts, observed, expected, host,
project, project_source) to state sink `friction/<yyyy-mm>.jsonl`, root
{{ORCH_LIB}}/rules/visibility.md §6, outside every worktree with any file-writing
tool; never skip the log. If refusal bars worktree writes, write where dispatch
permits; return path. Unresolved: project `null`, project_source `none`;
session/run/ticket/skill optional. Law:
{{ORCH_LIB}}/rules/improvement.md §1.
<!-- END ORCHFLOWS -->
