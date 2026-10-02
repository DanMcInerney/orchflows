# CI triage agent

Reads a failed CI build log and names the lines that show why the build failed. One model call per log, no tools.

Run by the runner as `python run_agent.py --workspace DIR --prompt-file FILE --transcript FILE --timeout SECONDS` (protocol: `interface/package.md`). `--print-command` prints the model command and the prompt for a workspace and calls nothing.

## Files

- `config.json`: model and effort (`claude-haiku-4-5`, `low`). `max_log_chars` is optional and defaults to 200,000.
- `prompt.md`: the triage prompt. `{{LOG}}` is replaced with the numbered log and `{{LINE_COUNT}}` with its line count.
- `run_agent.py`: reads `build.log`, builds the prompt, calls the model, writes `triage.json`.

## Behavior

- Lines are numbered from 1; a line ends at CRLF, LF or CR. ANSI sequences are removed and lines over 500 characters are cut.
- The model is called once: `claude -p --safe-mode --model <model> --effort <effort> --tools "" --permission-mode dontAsk --no-session-persistence --output-format json`, with the prompt on stdin. Safe mode keeps project and user instructions, skills, hooks and memory out of the call.
- A log whose numbered text exceeds `max_log_chars` is shortened: the first 40% and last 60% of the budget are kept, and a row marks the omitted lines.
- The reply is parsed as one JSON object (a fenced block or surrounding prose is tolerated). `triage.json` is written only when `failure_lines` holds two integers with `1 <= first <= last <= number of lines`; the summary is copied as text.
- The task's instruction file is not forwarded.

## Protocol statuses

- `completed`: the model replied; `triage.json` exists when the reply was usable. An unusable reply is a completed run without output.
- `refused`, `cut-off`: the model refused, or its reply hit an output limit.
- `timeout`: no result within `--timeout`; the model process and its children are stopped.
- `usage-limit`: the account's usage limit was reached.
- `error`: no `build.log`, the CLI could not run, it failed, or it returned an error result.

The transcript file holds the command, the prompt and the raw CLI output.
