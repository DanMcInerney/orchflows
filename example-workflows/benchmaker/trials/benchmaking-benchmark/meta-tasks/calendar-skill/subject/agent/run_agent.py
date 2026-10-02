"""Calendar-operations agent: Claude Haiku 4.5 working in the workspace with file and shell tools.

Invoked as: python run_agent.py --workspace DIR --prompt-file FILE --transcript FILE --timeout SECONDS
It prints one protocol JSON line on stdout (see the benchmark's interface/package.md). The task's prompt file is the
agent's prompt. Plugins listed under `skills` in config.json are loaded for the run.
"""
import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = "Read,Write,Edit,Bash,Glob,Grep"
EXIT = {"completed": 0, "refused": 0, "cut-off": 0, "error": 1, "timeout": 2, "usage-limit": 3}

_USAGE_LIMIT = re.compile(r"usage limit|hit your .{0,24}limit|limit reached|out of (?:extra )?usage|credit balance is too low", re.I)
_REFUSAL = re.compile(r"violate our usage policy|unable to respond to this request", re.I)


def skill_plugins(config: dict) -> list[Path]:
    """The plugin directories listed under `skills`, relative to this directory unless absolute."""
    found = []
    for entry in config.get("skills") or []:
        path = (HERE / entry).resolve()
        if not (path / ".claude-plugin" / "plugin.json").is_file():
            raise ValueError(f"skill {entry!r} is not a plugin directory (no .claude-plugin/plugin.json at {path})")
        found.append(path)
    return found


def isolation_settings(config_dir: str | None = None) -> dict:
    """Settings that keep hooks, auto-memory, synced claude.ai skills and the user's enabled plugins out of the run."""
    home = Path(config_dir or os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    try:
        plugins = json.loads((home / "settings.json").read_text(encoding="utf-8")).get("enabledPlugins", {})
    except (OSError, ValueError, AttributeError):
        plugins = {}
    return {"disableAllHooks": True, "syncClaudeAiSkills": False, "syncClaudeAiPlugins": False,
            "autoMemoryEnabled": False, "enabledPlugins": {name: False for name in plugins}}


def build_command(config: dict, plugins: list[Path], claude: list[str], config_dir: str | None = None) -> list[str]:
    """The Claude command; the prompt goes to stdin. Without a skill the run is in safe mode.

    A run with a skill cannot use safe mode, which disables plugins, so it isolates through settings instead;
    `safe_mode` in config.json overrides the choice for a run without a skill, to match the environment of a run with one."""
    safe = config.get("safe_mode")
    safe = not plugins if safe is None else bool(safe)
    if safe and plugins:
        raise ValueError("safe_mode disables plugins; a run with skills cannot use it")
    tools = config.get("tools", TOOLS)
    if plugins and "Skill" not in tools.split(","):
        tools += ",Skill"
    command = [*claude, "-p", "--verbose", "--output-format", "stream-json", "--model", config["model"],
               "--effort", config["effort"], "--permission-mode", "dontAsk", "--tools", tools, "--allowedTools", tools,
               "--no-session-persistence"]
    if safe:
        command.append("--safe-mode")
    else:
        command += ["--strict-mcp-config", "--setting-sources", "user", "--settings", json.dumps(isolation_settings(config_dir))]
    for plugin in plugins:
        command += ["--plugin-dir", str(plugin)]
    return command


def parse_events(stdout: str) -> list[dict]:
    events = []
    for line in stdout.splitlines():
        try:
            doc = json.loads(line)
        except ValueError:
            continue
        if isinstance(doc, dict):
            events.append(doc)
    return events


def classify(result: dict | None, exit_code: int | None, stderr: str) -> tuple[str, str]:
    """Protocol status and, for failures, the reason. The reply text is not searched for limit wording."""
    if result is None:
        text = stderr.strip()[-2000:] or f"no result event; exit code {exit_code}"
        return ("usage-limit" if _USAGE_LIMIT.search(text) else "error"), text
    reply = str(result.get("result") or "")
    if result.get("stop_reason") == "refusal" or (result.get("is_error") and _REFUSAL.search(reply)):
        return "refused", reply
    if result.get("is_error"):
        return ("usage-limit" if _USAGE_LIMIT.search(reply) or result.get("api_error_status") == 429 else "error"), reply
    if result.get("stop_reason") in ("max_tokens", "model_context_window_exceeded"):
        return "cut-off", reply
    return "completed", ""


def skill_calls(events: list[dict]) -> int:
    count = 0
    for event in events:
        content = (event.get("message") or {}).get("content") if event.get("type") == "assistant" else None
        count += sum(1 for item in content or [] if isinstance(item, dict) and item.get("type") == "tool_use" and item.get("name") == "Skill")
    return count


def _kill_tree(proc: subprocess.Popen) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    proc.kill()
    proc.wait()


def execute(command: list[str], prompt: str, cwd: Path, timeout: float) -> tuple[int | None, str, str]:
    """Run command in cwd with the prompt on stdin; output goes through files, not pipes. Exit code None means timeout."""
    env = {**os.environ, "CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS": "0"}
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp = Path(tmp)
        (tmp / "in").write_bytes(prompt.encode("utf-8"))
        with (tmp / "in").open("rb") as stdin, (tmp / "out").open("wb") as out, (tmp / "err").open("wb") as err:
            extra = {} if os.name == "nt" else {"start_new_session": True}
            proc = subprocess.Popen(command, cwd=cwd, env=env, stdin=stdin, stdout=out, stderr=err, **extra)
            try:
                code = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                _kill_tree(proc)
                code = None
        return (code, (tmp / "out").read_bytes().decode("utf-8", "replace"),
                (tmp / "err").read_bytes().decode("utf-8", "replace"))


def _record(path: str | None, command: list[str], prompt: str, stdout: str, exit_code: int | None, stderr: str) -> None:
    if not path:
        return
    lines = [json.dumps({"event": "call", "command": command, "prompt": prompt})]
    lines += [line for line in stdout.splitlines() if line.strip()]
    lines.append(json.dumps({"event": "return", "exit_code": exit_code, "stderr": stderr[-4000:]}))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def report(status: str, started: float, *, exit_code=None, model=None, cost=None, final: str = "", **extra) -> int:
    print(json.dumps({"status": status, "exit_code": exit_code, "seconds": round(time.monotonic() - started, 3),
                      "model": model, "cost_usd": cost, "final": final[-2000:], **extra}))
    return EXIT[status]


def main(argv=None, claude: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--prompt-file")
    parser.add_argument("--transcript")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--print-command", action="store_true", help="print the command and prompt, call nothing")
    args = parser.parse_args(argv)
    started, workspace = time.monotonic(), Path(args.workspace)
    try:
        config = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
        command = build_command(config, skill_plugins(config), claude or [shutil.which("claude") or "claude"])
        prompt = Path(args.prompt_file).read_text(encoding="utf-8") if args.prompt_file else ""
    except (OSError, ValueError, KeyError) as error:
        return report("error", started, final=str(error))
    if args.print_command:
        print(json.dumps({"command": command, "prompt": prompt, "cwd": str(workspace)}))
        return 0
    if not workspace.is_dir() or not prompt.strip():
        return report("error", started, final=f"workspace {workspace} does not exist" if not workspace.is_dir() else "the prompt file is missing or empty")
    try:
        exit_code, stdout, stderr = execute(command, prompt, workspace, args.timeout)
    except OSError as error:
        exit_code, stdout, stderr = 1, "", f"cannot start {command[0]}: {error}"
    _record(args.transcript, command, prompt, stdout, exit_code, stderr)
    events = parse_events(stdout)
    result = next((e for e in reversed(events) if e.get("type") == "result"), None)
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
    if exit_code is None:
        status, reason = "timeout", f"no result within {args.timeout:g} s"
    else:
        status, reason = classify(result, exit_code, stderr)
    usage = (result or {}).get("modelUsage")
    reply = str((result or {}).get("result") or "")
    return report(status, started, exit_code=exit_code, final=reply or reason,
                  model=next(iter(usage), None) if isinstance(usage, dict) and usage else init.get("model"),
                  cost=(result or {}).get("total_cost_usd"), turns=(result or {}).get("num_turns"), skill_calls=skill_calls(events),
                  plugins=[p.get("name") for p in init.get("plugins") or [] if isinstance(p, dict)])


if __name__ == "__main__":
    sys.exit(main())
