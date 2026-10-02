# $name

A benchmark for CI-failure triage: given the log of a failed build (`build.log`), a solver names the contiguous lines that show why the build failed (`triage.json`). It compares versions of a triage prompt and the models behind it. $n_tasks tasks from $n_groups source groups (repositories); stage: draft (see Limits).

$source_paragraph

## Run it

Python 3.11+, standard library only. From this folder:

```text
python run.py preflight                       # checks the package, runs the kit's self-check; no model calls
python run.py smoke --agent @reference --output out/smoke
python run.py full --agent @reference --output out/ref      # ceiling: computes the marked range, expect 1.0
python run.py full --agent @noop --output out/noop          # floor: delivers nothing, expect 0
python run.py full --agent adapters/haiku-low --output out/haiku    # the supplied prompt on Haiku 4.5 (model calls)
python run.py grade --input <dir of I/<task>/<submission>/ final workspaces> --output grades.jsonl
python run.py compare --a out/haiku --b out/sonnet --metric mean_credit
```

`full` runs every task with the suite's repeats (3). Pass your own agent directory (any directory with a `run_agent.py`, protocol in `benchkit/INTERFACE.md`) in place of an adapter. `adapters/haiku-low` and `adapters/sonnet-low` are the supplied triage agent with two model settings: one `claude -p` call per log, no tools. `launch_budget` is $launch_budget; no retries are declared.

## What a solver receives and delivers

Workspace: `build.log` only (UTF-8; ANSI sequences and carriage returns possible). Prompt: `tasks/<id>/instruction.md`, outside the workspace. Deliverable: `triage.json` in the workspace root, `{"failure_lines": [first, last], "summary": "..."}`, 1-based inclusive line numbers; a line ends at CRLF, LF or CR. The instruction states the grading rule.

## Grading

`tasks/<id>/tests/verify.py` compares `failure_lines` with the failure text a person marked in the log (`tests/expected.json` holds the marked lines and their text). Coverage is the share of marked lines inside the range; focus is the share of range lines on or within 2 lines of the failure; credit is their average. A range holding no marked line, or with under a quarter of its lines near the failure, earns nothing, so dumping the log earns nothing. Full success needs both at least 0.8. Valid JSON in any layout is accepted (whitespace, key order, extra keys, BOM, escapes, integral floats); anything else earns nothing. The summary is not graded. Details and constants are in the verifier's docstring.

## Contents

| Path | What |
| --- | --- |
| `suite.json`, `card.json` | profiles, repeats, budgets; the quality card with typed claims |
| `tasks/<id>/` | instruction, `environment/build.log`, `solution/solve.py`, `tests/verify.py`, `tests/expected.json`, `task.toml` |
| `admission/<id>/` | admission evidence: `admission.json`, and `labeled/<submission>/triage.json` with `labels.json` (valid and wrong outcomes and the credit the rule gives each) |
| `adapters/` | the supplied agent as `haiku-low` and `sonnet-low` |
| `research/catalog.md`, `rejections.jsonl` | sources and scenario catalog; every candidate's disposition |
| `run.py`, `benchkit/` | the runner (copied from the kit) |

## Tasks

$families_table

## Scripted baselines (computed from the labels, no model)

What obvious scripts would score on these tasks under the documented rule:

$baselines_table

## Limits

- No model has been run. Haiku 4.5 and Sonnet 5.5 have no measured rates here; difficulty, headroom and separation between prompt versions are unmeasured, and the card says so.
- Admission is partial: the reference, trivial attempts and labeled outcomes ran through the verifier; no fresh auditor, adversary, realism reviewer, calibration or known-order check did.
- Labels are one person's marking of one failure; a log can hold other valid explanations. Marked text that repeats in a log counts at every occurrence.
- $exposure_note
- The solver runs as the same OS user as the runner: staging keeps the package out of the workspace, but reading it by absolute path is not prevented.
