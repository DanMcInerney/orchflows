<!-- BEGIN ORCHFLOWS (managed block — do not edit inside; reinstall to update) -->
# orchflows

`orch-` terms mean what {{ORCH_DOCS}}/vocabulary.md defines.

- Root routes, launches what a door emits, and lands
  returns; relay a `kind: user-only` question verbatim. Never author a
  role-bearing payload. Prompt-less or wrong-profile role-bearing work refuses;
  `role: none` only orchestrates. `orch-off` suspends automatic routing; named
  items still run only when named. Route smallest-first: **answer** — context
  evidence decides; **single** — one [ticket]({{ORCH_LIB}}/contracts/work-item.md)
  carrying Goal, Context, and optional Details takes `new --file`, then
  `tickets.py dispatch` and `land`. **graph** — open the journal:
  `tickets.py frame-open <run>`. Each wave, re-read that frame's
  `## Report` and its children, then per ready intent run
  `tickets.py do <run> --pack <pack> --goal-file <f> [--parent <frame>] [--workspace <tree>]`, or
  `judge` over the artifacts it is handed; invoke the emitted `launch`
  verbatim adding nothing to its prompt, then `tickets.py land` its return:
  it reads the ticket's `done`, integrates, and prints the frontier it freed. Declaring
  none, grade it yourself with `land --status`. Append every decision through
  `result`, relaying each `artifact:` and `findings:` line verbatim. End at
  `frame-close`; `orchflows resume` lists open frames. **outline** — one
  planner runs a planning `orch-do` that seals the root this route drives.
  The planner never drives the run. Skill/workflow/pack/contract/router work carries
  `{{ORCH_LIB}}/docs/custom-workflow-authoring.md` in Context. **fix** — a known
  cause enters single; an unknown or unverified cause enters outline. `install.py
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
