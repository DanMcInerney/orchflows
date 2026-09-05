<!-- BEGIN ORCHFLOWS (managed block — do not edit inside; reinstall to update) -->
# orchflows

`orch-` terms mean what {{ORCH_DOCS}}/vocabulary.md defines.

- Root routes, launches emissions, and lands
  returns; relay `kind: user-only` questions verbatim. Never author a
  role-bearing payload. Prompt-less or wrong-profile work refuses;
  `role: none` only orchestrates. `orch-off` suspends routing; named
  items still run only when named. Route smallest-first; say the lane before
  work. Named workflows and user cost choices win; otherwise reuse
  primitives, reserving workflows for sequence, recurrence, resume, independence,
  or audit value. **direct** — context evidence decides; direct changes need
  checks and commit records; no trace, no act. `role: none` roots run derived
  deterministic commands only. **worker** — isolation, fresh context, or checked landing takes
  `tickets.py do <run> --standard <standard> --goal-file <f> [--parent <frame>]
  [--workspace <tree>]`, or `judge` over artifacts; invoke the emitted `launch`
  verbatim, then `tickets.py land`: it reads `done`,
  integrates. Undeclared grades `land --status`. **team** — children,
  resume, or audit trails record shape through `tickets.py frame-open <run>
  --shape "<line>"`; each wave re-read its `## Report`; decide through
  `result`, relaying `artifact:` and `findings:` lines verbatim; children
  run scoped checks; suite runs at close; end at `frame-close`, judging
  seams or saying `unjudged: <reason>`; `orchflows resume` lists
  frames. **plan** — an unresolved goal seals through one planning
  `orch-do`; the planner never drives. Tripwires promote, never
  predict: a second concern mid-direct enters worker; splitting scope
  enters team; an unknown cause investigates before any edit; resolved
  uncertainty de-escalates.
  Skill/workflow/standard/contract/router work carries
  `{{ORCH_LIB}}/docs/custom-workflow-authoring.md` in Context.
  `install.py doctor` diagnoses; `evolve`/`benchmaker`/
  `skill-tournament` run only when named.
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
({{ORCH_LIB}}/rules/visibility.md §6) outside worktrees; never skip it. If refusal bars
worktree writes, write where dispatch permits and return the path. Unresolved:
project `null`, project_source `none`; session/run/ticket/skill optional. Law:
{{ORCH_LIB}}/rules/improvement.md §1.
<!-- END ORCHFLOWS -->
