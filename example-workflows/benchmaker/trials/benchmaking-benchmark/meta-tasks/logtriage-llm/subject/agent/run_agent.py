"""CI-failure triage agent: one model call over the numbered build log, answer written to triage.json.

Invoked as: python run_agent.py --workspace DIR --prompt-file FILE --transcript FILE --timeout SECONDS
It prints one protocol JSON line on stdout (see the benchmark's interface/package.md). The task prompt file is
not forwarded: the triage prompt is prompt.md, as in the team's pipeline.
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
LOG, ANSWER = "build.log", "triage.json"
MAX_LOG_CHARS = 200_000   # numbered log characters sent to the model; head and tail are kept beyond this
MAX_LINE_CHARS = 500
HEAD_SHARE = 0.4
EXIT = {"completed": 0, "refused": 0, "cut-off": 0, "error": 1, "timeout": 2, "usage-limit": 3}

_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b")
_BREAK = re.compile(r"\r\n|\n|\r")
_USAGE_LIMIT = re.compile(r"usage limit|hit your .{0,24}limit|limit reached|out of (?:extra )?usage|credit balance is too low", re.I)
_REFUSAL = re.compile(r"violate our usage policy|unable to respond to this request", re.I)


def split_lines(text: str) -> list[str]:
    """Lines end at CRLF, LF or CR; a final line break does not start another line."""
    lines = _BREAK.split(text)
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def numbered(lines: list[str], max_chars: int = MAX_LOG_CHARS) -> str:
    rows = []
    for number, line in enumerate(lines, 1):
        text = _ANSI.sub("", line).rstrip()
        if len(text) > MAX_LINE_CHARS:
            text = text[:MAX_LINE_CHARS] + " ...[line cut]"
        rows.append(f"{number:>6} | {text}")
    if sum(len(r) + 1 for r in rows) <= max_chars:
        return "\n".join(rows)
    head, tail, used = [], [], 0
    for row in rows:
        if used + len(row) + 1 > max_chars * HEAD_SHARE:
            break
        head.append(row)
        used += len(row) + 1
    used = 0
    for row in reversed(rows[len(head):]):
        if used + len(row) + 1 > max_chars * (1 - HEAD_SHARE):
            break
        tail.append(row)
        used += len(row) + 1
    skipped = len(rows) - len(head) - len(tail)
    return "\n".join(head + [f"       ... {skipped} lines omitted ..."] + tail[::-1])


def build_prompt(template: str, lines: list[str], max_chars: int = MAX_LOG_CHARS) -> str:
    return template.replace("{{LINE_COUNT}}", str(len(lines))).replace("{{LOG}}", numbered(lines, max_chars))


def build_command(config: dict, claude: list[str]) -> list[str]:
    return [*claude, "-p", "--safe-mode", "--model", config["model"], "--effort", config["effort"],
            "--tools", "", "--permission-mode", "dontAsk", "--no-session-persistence", "--output-format", "json"]


def parse_output(stdout: str) -> dict | None:
    """The final result object of `--output-format json` (a single object, or a list of messages)."""
    for text in (stdout, stdout.strip().rsplit("\n", 1)[-1]):
        try:
            doc = json.loads(text)
            break
        except ValueError:
            continue
    else:
        return None
    if isinstance(doc, list):
        doc = next((m for m in reversed(doc) if isinstance(m, dict) and m.get("type") == "result"), None)
    return doc if isinstance(doc, dict) and doc.get("type", "result") == "result" else None


def classify(result: dict | None, exit_code: int | None, stderr: str) -> tuple[str, str]:
    """Protocol status and, for failures, the reason. The reply text is not searched for limit wording."""
    if result is None:
        text = stderr.strip()[-2000:] or f"no result object; exit code {exit_code}"
        return ("usage-limit" if _USAGE_LIMIT.search(text) else "error"), text
    reply = str(result.get("result") or "")
    if result.get("stop_reason") == "refusal" or (result.get("is_error") and _REFUSAL.search(reply)):
        return "refused", reply
    if result.get("is_error"):
        return ("usage-limit" if _USAGE_LIMIT.search(reply) else "error"), reply
    if result.get("stop_reason") in ("max_tokens", "model_context_window_exceeded"):
        return "cut-off", reply
    return "completed", ""


def extract_triage(reply: str, lines: int) -> tuple[dict | None, str]:
    text = reply.strip()
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, re.S)
    braces = [text[text.find("{"):text.rfind("}") + 1]] if "{" in text and "}" in text else []
    for candidate in [text, *fenced, *braces]:
        try:
            doc = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(doc, dict):
            break
    else:
        return None, "the reply holds no JSON object"
    span = doc.get("failure_lines")
    if not (isinstance(span, list) and len(span) == 2 and all(type(v) is int for v in span)):
        return None, "failure_lines is not a list of two integers"
    if not 1 <= span[0] <= span[1] <= lines:
        return None, f"failure_lines {span} is outside lines 1-{lines}"
    summary = doc.get("summary")
    return {"failure_lines": span, "summary": summary if isinstance(summary, str) else ""}, ""


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


def execute(command: list[str], prompt: str, timeout: float) -> tuple[int | None, str, str]:
    """Run command with the prompt on stdin; output goes through files, not pipes. Exit code None means timeout."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp = Path(tmp)
        (tmp / "in").write_bytes(prompt.encode("utf-8"))
        with (tmp / "in").open("rb") as stdin, (tmp / "out").open("wb") as out, (tmp / "err").open("wb") as err:
            extra = {} if os.name == "nt" else {"start_new_session": True}
            proc = subprocess.Popen(command, stdin=stdin, stdout=out, stderr=err, **extra)
            try:
                code = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                _kill_tree(proc)
                code = None
        return (code, (tmp / "out").read_bytes().decode("utf-8", "replace"),
                (tmp / "err").read_bytes().decode("utf-8", "replace"))


def _record(path: str | None, events: list[dict]) -> None:
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8", newline="\n")


def main(argv=None, claude: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--prompt-file")
    parser.add_argument("--transcript")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--print-command", action="store_true", help="print the command and prompt, call nothing")
    args = parser.parse_args(argv)
    config = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    workspace = Path(args.workspace)
    log = workspace / LOG
    claude = claude or [shutil.which("claude") or "claude"]
    started = time.monotonic()
    events: list[dict] = []
    status, reason, model, cost, exit_code, final = "error", "", None, None, None, ""
    if not log.is_file() and not args.print_command:
        reason = f"no {LOG} in the workspace"
    else:
        lines = split_lines(log.read_bytes().decode("utf-8", errors="replace")) if log.is_file() else []
        prompt = build_prompt((HERE / "prompt.md").read_text(encoding="utf-8"), lines, int(config.get("max_log_chars", MAX_LOG_CHARS)))
        command = build_command(config, claude)
        if args.print_command:
            print(json.dumps({"command": command, "prompt": prompt}))
            return 0
        if not lines:
            status, final = "completed", "empty log; nothing to triage"
        else:
            events.append({"event": "call", "command": command, "prompt": prompt})
            try:
                exit_code, stdout, stderr = execute(command, prompt, args.timeout)
            except OSError as error:
                exit_code, stdout, stderr = 1, "", f"cannot start {command[0]}: {error}"
            events.append({"event": "return", "exit_code": exit_code, "stdout": stdout, "stderr": stderr})
            if exit_code is None:
                status, reason = "timeout", f"no result within {args.timeout:g} s"
            else:
                result = parse_output(stdout)
                status, reason = classify(result, exit_code, stderr)
                if result is not None:
                    cost = result.get("total_cost_usd")
                    usage = result.get("modelUsage")
                    model = next(iter(usage), None) if isinstance(usage, dict) else None
                    final = str(result.get("result") or "")
                if status == "completed":
                    triage, problem = extract_triage(final, len(lines))
                    if triage:
                        (workspace / ANSWER).write_text(json.dumps(triage, indent=2) + "\n", encoding="utf-8", newline="\n")
                    else:
                        events.append({"event": "no-answer", "reason": problem})
    _record(args.transcript, events)
    print(json.dumps({"status": status, "exit_code": exit_code, "seconds": round(time.monotonic() - started, 3),
                      "model": model, "cost_usd": cost, "final": final or reason}))
    return EXIT[status]


if __name__ == "__main__":
    sys.exit(main())
