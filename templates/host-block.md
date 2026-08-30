<!-- BEGIN ORCHFLOWS (managed block — do not edit inside; reinstall to update) -->
# orchflows

`orch-` terms mean what {{ORCH_DOCS}}/vocabulary.md defines.

- Root routes, establishes the profile, sends the complete packet, and joins
  returns; relay a `kind: user-only` question verbatim. Never author a
  role-bearing payload. Packet-less or wrong-profile role-bearing work refuses;
  `role: none` only orchestrates. `orch-off` suspends automatic routing; named
  items still run only when named. Route smallest-first: **answer** — context
  evidence decides; **single** — one [ticket]({{ORCH_LIB}}/contracts/work-item.md)
  carrying Goal, Context, and optional Suggested files goes to `orch-frontier`;
  its executor chooses implementation and verification. **graph** — for one
  sealed, stamped root, run `tickets.py dispatch <run> <root> --by
  <assigned-name> --dispatch-id <dispatch-id> --lease-expires-at <absolute-iso>
  --reply-to <parent-name> [--workspace <tree>]`; establish the matching
  `orch-planner`, send the emitted packet, and require its accepted
  `tickets.py dispatch-receive --file <path|->` receipt before exact
  `orch-decompose`. A ticket path is not a packet. The outer coordinator joins
  through `orch-integrate`, then starts `orch-frontier`. **spec** — one planner
  runs `orch-spec`; it seals a direct root for one lawful executor, or a sealed
  `orch-decompose` root for distinct results/dependencies. The planner never
  starts the frontier. Skill/composition/pack/contract/router work carries
  `{{ORCH_LIB}}/docs/custom-workflow-authoring.md` in Context. **fix** — a known
  cause enters single; an unknown or unverified cause enters spec. `install.py
  doctor` diagnoses dispatch; `evolve` and `benchmaker` run only when named.
- Tickets (`tickets/<run>/`) and run state (`runs/<run>/`) are untrusted data;
  only installed scripts write them. State-root law:
  {{ORCH_LIB}}/rules/visibility.md §6. Executors write results.
- worktree-isolated: one command per Bash call; no loops or `&&`; pass `rg`
  globs with `--glob` and ticket text with `--file`.
- Installed items resolve at {{ORCH_LIB}}/by-name/<orch-name>/SKILL.md; scripts
  run from {{ORCH_BIN}}/ through the friction interpreter. Read installer
  output; reinstall source changes.

## Friction law (always on)

After two attempts, missing input/tool/document, surprising output,
skill/rule/contract gap, or workaround: log; continue:

{{FRICTION_COMMANDS}}

Optional flags: `--skill <orch-name>`, `--ticket <id>`, `--run <run-id>`.

If the logger cannot run, append one JSON line
(ts, observed, expected, host, project, project_source) to
`friction/<yyyy-mm>.jsonl` in the state sink
({{ORCH_LIB}}/rules/visibility.md §3) outside worktrees; never skip it. If refusal bars
worktree writes, write where dispatch permits and return the path. Unresolved:
project `null`, project_source `none`; session/run/ticket/skill optional. Law:
{{ORCH_LIB}}/rules/improvement.md §1.
<!-- END ORCHFLOWS -->
