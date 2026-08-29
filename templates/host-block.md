<!-- BEGIN ORCHFLOWS (managed block — do not edit inside; reinstall to update) -->
# orchflows

`orch-` terms mean what {{ORCH_DOCS}}/vocabulary.md defines.

- Root routes, establishes profile, sends, joins;
  relay `kind: user-only` question verbatim; never author role-bearing
  payloads. Packet-less/wrong-profile refuses. `role: none` orchestrates,
  never authors artifacts. `orch-off` suspends routing; a named item runs as
  named, everything else only when named. Route smallest-first by shape:
  **answer** — evidence in context decides it; **single** —
  [ticket]({{ORCH_LIB}}/contracts/work-item.md) with semantic payload Goal, Context,
  optional Suggested files goes to `orch-frontier`;
  executor chooses implementation/verification. **graph** — stamped root: invoke
  `tickets.py dispatch <run> <root> --by <assigned-name> --dispatch-id
  <dispatch-id> --lease-expires-at <absolute-iso> --reply-to <parent-name>
  [--workspace <tree>]`; it atomically performs readiness, workspace and
  evidence-store establishment, attempt opening, and packet
  projection, retaining its
  `workspace_path` and returning a packet or unchanged refusal. Establish
  `orch-planner` child. Send the
  emitted packet. Its response `.packet` goes by file/stdin; child runs
  `tickets.py dispatch-receive` with `--file <path>` or `--file -`. A durable
  accepted receipt is required; then start exact `orch-decompose`.
  ticket path is not a packet; outer coordinator integrates, starts
  `orch-frontier`. **spec** — same planner child runs
  `orch-spec`: seal direct root for a lawful executor; for distinct
  outcomes or dependencies, take a sealed `orch-decompose` root through
  `tickets.py dispatch`, then run `orch-decompose`.
  outer coordinator integrates, starts `orch-frontier`. Planner never persists
  ticket sequences/starts frontier. Skill/composition/pack/contract/router
  work uses those routes; seal `{{ORCH_LIB}}/docs/custom-workflow-authoring.md`
  in Context. Known cause
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
  output; reinstall changes.

## Friction law (always on)

After two attempts, missing input/tool/document, surprising output,
skill/rule/contract gap, or workaround: log; continue:

{{FRICTION_COMMANDS}}

Optional flags: `--skill <orch-name>`, `--ticket <id>`, `--run <run-id>`.

Whenever the logger cannot run, append one JSON line (ts, observed, expected, host,
project, project_source) to state sink `friction/<yyyy-mm>.jsonl`, root
{{ORCH_LIB}}/rules/visibility.md §6, outside worktrees with any file-writing
tool; never skip the log. If refusal bars worktree writes, write where dispatch
permits; return path. Unresolved: project `null`, project_source `none`;
session/run/ticket/skill optional. Law:
{{ORCH_LIB}}/rules/improvement.md §1.
<!-- END ORCHFLOWS -->
