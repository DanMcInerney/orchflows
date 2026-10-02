# Interface: CI build-log triage

## Agents

An agent is a directory containing `run_agent.py`, run as described in `interface/package.md` with the task workspace as its working directory and the task's instruction file passed as `--prompt-file`. The shipped agent, `./subject/agent/`, makes one model call per log and ignores the instruction file; its prompt is `prompt.md` there.

## Workspace

Input: `build.log`, UTF-8 text from a CI run. It can be a whole log or an excerpt, and it can contain ANSI color sequences and carriage returns.

Output: `triage.json` in the workspace root:

```json
{"failure_lines": [212, 231], "summary": "test_render_table_width fails an assertion about table width."}
```

- `failure_lines` is `[first, last]`: integers, 1-based, both lines included, `first <= last`, both inside `build.log`. It is one contiguous range of the lines that show why the build failed.
- `summary` is a short plain-text description of the failure.
- Other keys are ignored.

## Lines

Line numbers refer to `build.log` as delivered to the agent. A line ends at CRLF, LF or CR. A final line break does not start another line.

## What the shipped agent does with a log

- It numbers lines itself, removes ANSI sequences, and cuts lines longer than 500 characters.
- It sends at most about 200,000 characters of the numbered log. For a longer log it keeps the first 40% and the last 60% of that budget and marks the omitted lines; line numbers stay those of `build.log`.
- It writes `triage.json` only when the model's reply holds a valid `failure_lines`; otherwise the task has no output.

Details are in `subject/agent/README.md`.
