# schedule-nosolver benchmark

Measures how well an assistant schedules one meeting across several people's calendars: who must attend, each person's work hours in their own UTC offset, busy time over several days, personal limits, rooms and a preference for the earliest or latest time, or the honest answer that no time works. No scheduling assistant exists yet, so the benchmark runs a stock agent (`adapters/haiku-low`, `adapters/sonnet-low`) through the same agent directory interface a real assistant will use.

This package holds <<TASKS>> tasks in <<FAMILIES>> families from <<GROUPS>> source groups (split: <<SPLIT>>). The card (`card.json`) is a draft: the verifier, the reference solution and the do-nothing floors are validated; no model has been run, so headroom and the order of the stock agents are open.

## Run it

```text
python run.py preflight                                    checks everything without running a solver
python run.py smoke --agent @reference --output out        a few tasks, one attempt each
python run.py full --agent adapters/haiku-low --output out all tasks, 3 repeats each (needs the claude CLI)
python run.py grade --input submissions --output grades.jsonl   grade final workspaces: submissions/<task>/<name>/output.json
```

`@reference` runs each task's `solution/solve.py` and `@noop` does nothing; neither makes a model call. `python run.py --help` lists the other commands (`quick`, `resume`, `rescore`, `compare`); `benchkit/INTERFACE.md` describes the records.

## Solver interface

An agent is a directory with `run_agent.py`, run as `python run_agent.py --workspace DIR --prompt-file FILE --transcript FILE --timeout SECONDS`. The workspace holds the task's `input.json`; the prompt file is the task's `instruction.md`. The agent writes `output.json` in the workspace: `{"start", "end", "room"}` or `{"infeasible": true, "explanation": "..."}`. It prints one JSON line with its status (`benchkit/INTERFACE.md`).

## Scoring

Each task is graded from the captured workspace against the task's own `environment/input.json`. Timestamps are compared as instants, so any offset, key order, whitespace or extra key is accepted, and for `any` every valid slot is. Two dimensions: `valid` (0.6), the slot breaks no rule or the infeasibility claim is right, and `optimal` (0.4), the slot is the earliest or latest valid one, or an infeasibility claim carries its explanation. Full success needs both. Doing nothing earns 0; a uniformly random well-formed slot is expected to earn about <<RANDOM>>.

## Layout

`tasks/<id>/` instruction, environment (`input.json`), reference solution and verifier. `admission/<id>/` labelled outputs (valid variants, valid-but-not-optimal, invalid) with `labels.json`, and the admission evidence. `research/catalog.md` the scenario catalog and sources. `rejections.jsonl` every candidate and its disposition. `adapters/` the stock agents.

## Limits

Requests are synthetic, authored from the interface and the style of Natural Plan's calendar scheduling (CC BY 4.0); no logged user requests are involved. Offsets are fixed, so daylight saving and named time zones are not covered. One meeting per task. The tasks are public, so results support development claims only. Requires Python 3.11 or later and no other packages; the stock agents need the `claude` CLI.
