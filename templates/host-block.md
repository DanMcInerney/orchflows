<!-- BEGIN ORCHFLOWS (managed block — do not edit inside; reinstall to update) -->
# orchflows

`orch-` terms mean what {{ORCH_DOCS}}/vocabulary.md defines.

- Root routes, launches what a door emits, and lands
  returns; relay a `kind: user-only` question verbatim. Never author a
  role-bearing payload. Prompt-less or wrong-profile role-bearing work refuses;
  `role: none` only orchestrates. `orch-off` suspends automatic routing; named
  items still run only when named. Route by need, smallest first. **act** —
  context evidence decides an answer; a change this session can make, check,
  and record itself — the commit is the record; no trace, no act. A
  `role: none` root never acts: derived deterministic commands only,
  authoring nothing. **brick** — isolation, a fresh context, or a checked
  landing takes one `tickets.py do <run> --pack <pack> --goal-file <f>
  [--parent <frame>] [--workspace <tree>]`, or `judge` over handed artifacts;
  invoke the emitted `launch` verbatim, then `tickets.py land`: it reads
  `done`, integrates, prints the freed frontier. Declaring none grades with
  `land --status`. **frame** — children, resume, or an audit trail opens
  `tickets.py frame-open <run>`; each wave re-read its `## Report`; append
  decisions through `result`, relaying `artifact:` and `findings:` lines
  verbatim; children run scoped checks; the suite runs once, at close; end at
  `frame-close`, judging the seams or saying `unjudged: <reason>`;
  `orchflows resume` lists open frames. **outline** — an unresolved goal
  seals through one planning `orch-do`; the planner never drives. Tripwires
  promote, never predict: an unknown cause investigates before any edit.
  Skill/workflow/pack/contract/router work carries
  `{{ORCH_LIB}}/docs/custom-workflow-authoring.md` in Context. `install.py
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
