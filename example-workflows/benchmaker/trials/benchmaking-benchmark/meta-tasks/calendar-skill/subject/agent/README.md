# Calendar-operations agent

Books meetings by editing the team's calendar files in its workspace, under the team's booking policy. One Claude session per task, with the tools `Read`, `Write`, `Edit`, `Bash`, `Glob` and `Grep`.

Run by the runner as `python run_agent.py --workspace DIR --prompt-file FILE --transcript FILE --timeout SECONDS` (protocol: `interface/package.md`). `--print-command` prints the Claude command and the prompt and calls nothing.

## Files

- `config.json`: `model` (`claude-haiku-4-5`), `effort` (`low`) and `skills`, a list of plugin directories to load, empty by default. Optional keys: `tools` replaces the tool list, and `safe_mode` overrides the isolation choice described below.
- `run_agent.py`: starts the session in the workspace with the task's prompt file as its prompt, and reports the outcome.

## Behavior

- The command is `claude -p --verbose --output-format stream-json --model <model> --effort <effort> --permission-mode dontAsk --tools <tools> --allowedTools <tools> --no-session-persistence`, with the prompt on stdin and the workspace as the working directory.
- With no skill listed the session runs in `--safe-mode`, which keeps user and project instructions, skills, plugins, hooks and memory out of it.
- With a skill listed it cannot use safe mode, which disables plugins. The session instead gets `--plugin-dir` for each listed plugin, `Skill` added to its tools, `--strict-mcp-config`, `--setting-sources user` and settings that turn off hooks, auto-memory, synced claude.ai skills and the user's enabled plugins. A skill entry is a plugin directory, relative to this directory or absolute, for example `"skills": ["../booking-rules"]`.
- To compare a run with a skill against one without at the same isolation, set `"safe_mode": false` in the run without one, or run both with a Claude home that holds no user skills or instructions. User-level skills and `CLAUDE.md` still load when safe mode is off.
- The model decides whether to invoke a skill from its description; the prompt does not name it.

## Protocol statuses

- `completed`: the session ended with a result. The workspace holds whatever the agent left in it.
- `refused`, `cut-off`: the model refused, or its reply hit an output limit.
- `timeout`: no result within `--timeout`; the session and its child processes are stopped.
- `usage-limit`: the account's usage limit was reached.
- `error`: the prompt file or workspace is missing, a listed skill is not a plugin directory, the CLI could not run, or it returned an error result.

The line also reports `turns`, `skill_calls` (how many times the session invoked a skill) and the `plugins` the session loaded. The transcript file holds the command, the prompt and the raw event stream.
