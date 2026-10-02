# calendar-skill benchmark

Measures whether the `booking-rules` skill makes a calendar-operations agent better at booking a meeting by editing a team's calendar files under its booking policy. Each task is a workspace: `request.json`, the policy (`policy.json` and the rendered `policy.md`), one calendar file per person and, mostly, room files. The agent adds the meeting to the right files, or says that no valid time exists, and must leave every existing entry alone. The same tasks run with the skill (`adapters/haiku-low-skill`) and without it (`adapters/haiku-low`), at the same model, tools, settings isolation and budget.

This package holds <<TASKS>> tasks in <<FAMILIES>> families from <<GROUPS>> source groups (split: <<SPLIT>>). The card (`card.json`) is a draft: the verifier, the reference solution and the do-nothing floors are validated; no model has been run, so the skill's uplift is open.

## Run it

```text
python run.py preflight                                          checks everything without running a solver
python run.py smoke --agent @reference --output out              a few tasks, one attempt each
python run.py full --agent adapters/haiku-low-skill --output a   all tasks, 3 repeats each (needs the claude CLI)
python run.py full --agent adapters/haiku-low --output b
python run.py compare --a a --b b --metric mean_credit           paired per-task differences with intervals
python run.py grade --input submissions --output grades.jsonl    grade final workspaces: submissions/<task>/<name>/
```

`@reference` runs each task's `solution/solve.py` and `@noop` does nothing; neither makes a model call. `python run.py --help` lists the other commands (`quick`, `resume`, `rescore`); `benchkit/INTERFACE.md` describes the records.

## Solver interface

An agent is a directory with `run_agent.py`, run as `python run_agent.py --workspace DIR --prompt-file FILE --transcript FILE --timeout SECONDS`. The workspace holds the task's files; the prompt file is the task's `instruction.md`. The agent's deliverable is the final state of the workspace: the edited calendar and room files and `result.json`. It prints one JSON line with its status (`benchkit/INTERFACE.md`). The adapters' `config.json` says how a skill is loaded.

## Scoring

Each task is graded from the captured workspace against the task's own original `environment/` files. Times are compared as instants, so any offset, key order, whitespace or extra key is accepted, and for `any` every valid slot is. Three dimensions, each earned only by a valid outcome: `valid` (0.6), the files hold one new entry per attendee and in the booked room at a slot that meets every rule and the policy (or the infeasible request is declared infeasible and nothing is added); `optimal` (0.2), the slot is the earliest or latest valid one, or an infeasibility answer carries its explanation; `reported` (0.2), `result.json` is accurate about the files. Changing or removing an existing entry or file, or reporting a booking no file holds, is a critical failure and defeats full success. Doing nothing earns 0; a uniformly random well-formed booking is expected to earn about <<RANDOM>>.

## Layout

`tasks/<id>/` instruction, environment (the workspace), reference solution and verifier. `admission/<id>/` labelled final workspaces (valid variants, valid-but-not-optimal, invalid, damaged files) with `labels.json`, and the admission evidence. `research/catalog.md` the scenario catalog and sources. `rejections.jsonl` every candidate and its disposition. `adapters/` the stock agent with and without the skill.

## Limits

Workspaces are synthetic, authored from the interface and the style of Natural Plan's calendar scheduling (CC BY 4.0); the team policy is invented for this benchmark. Offsets are fixed, so daylight saving and named time zones are not covered. One meeting per task. The tasks are public, so results support development claims only. Requires Python 3.11 or later and no other packages; the adapters need the `claude` CLI, and the skill arm needs `--plugin-dir` to load the skill in print mode, which a first run has to confirm.
