"""Stand-in scheduling assistant: one Claude call that reads input.json and writes output.json.

Invoked as: python run_agent.py --workspace DIR --prompt-file FILE --transcript FILE --timeout SECONDS
It prints one protocol JSON line on stdout (see the benchmark's interface/package.md). The model and effort come
from config.json beside this file; the call has no tools, so the task's instruction and input.json go in the prompt.
This is the stock agent the benchmark names as the system it measures until a real assistant plugs in.
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
EXIT = {"completed": 0, "refused": 0, "cut-off": 0, "error": 1, "timeout": 2, "usage-limit": 3}
_USAGE_LIMIT = re.compile(r"usage limit|hit your .{0,24}limit|limit reached|out of (?:extra )?usage|credit balance is too low", re.I)
_REFUSAL = re.compile(r"violate our usage policy|unable to respond to this request", re.I)


def build_command(config: dict, claude: list[str]) -> list[str]:
    return [*claude, "-p", "--safe-mode", "--model", config["model"], "--effort", config["effort"], "--tools", "",
            "--permission-mode", "dontAsk", "--no-session-persistence", "--output-format", "json"]


def build_prompt(instruction: str, data: str) -> str:
    return (f"{instruction.rstrip()}\n\nYou have no tools in this session, so the files are shown here instead.\n\n"
            f"`input.json`:\n```json\n{data.strip()}\n```\n\nReply with only the JSON object to write to `output.json`.")


def parse_output(stdout: str) -> dict | None:
    """The result object of `--output-format json` (one object, or a list of messages)."""
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


def extract_answer(reply: str) -> dict | None:
    """The first JSON object in the reply: the whole text, a fenced block or the outermost braces."""
    text = reply.strip()
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, re.S)
    braces = [text[text.find("{"):text.rfind("}") + 1]] if "{" in text and "}" in text else []
    for candidate in [text, *fenced, *braces]:
        try:
            doc = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(doc, dict):
            return doc
    return None


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
        return (code, (tmp / "out").read_bytes().decode("utf-8", "replace"), (tmp / "err").read_bytes().decode("utf-8", "replace"))


def report(status: str, started: float, *, exit_code=None, model=None, cost=None, final: str = "") -> int:
    print(json.dumps({"status": status, "exit_code": exit_code, "seconds": round(time.monotonic() - started, 3),
                      "model": model, "cost_usd": cost, "final": final[-2000:]}))
    return EXIT[status]


def main(argv=None, claude: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--prompt-file")
    parser.add_argument("--transcript")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--print-command", action="store_true", help="print the command and prompt, call nothing")
    args = parser.parse_args(argv)
    started, workspace = time.monotonic(), Path(args.workspace)
    try:
        config = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
        command = build_command(config, claude or [shutil.which("claude") or "claude"])
        instruction = Path(args.prompt_file).read_text(encoding="utf-8") if args.prompt_file else ""
        data = (workspace / "input.json").read_text(encoding="utf-8")
    except (OSError, ValueError, KeyError) as error:
        return report("error", started, final=str(error))
    prompt = build_prompt(instruction, data)
    if args.print_command:
        print(json.dumps({"command": command, "prompt": prompt, "cwd": str(workspace)}))
        return 0
    try:
        exit_code, stdout, stderr = execute(command, prompt, args.timeout)
    except OSError as error:
        exit_code, stdout, stderr = 1, "", f"cannot start {command[0]}: {error}"
    if args.transcript:
        Path(args.transcript).parent.mkdir(parents=True, exist_ok=True)
        Path(args.transcript).write_text(json.dumps({"command": command, "prompt": prompt}) + "\n" + stdout + "\n" + json.dumps(
            {"exit_code": exit_code, "stderr": stderr[-4000:]}) + "\n", encoding="utf-8")
    result = parse_output(stdout)
    if exit_code is None:
        return report("timeout", started, final=f"no result within {args.timeout:g} s")
    status, reason = classify(result, exit_code, stderr)
    reply = str((result or {}).get("result") or "")
    answer = extract_answer(reply) if status == "completed" else None
    if answer is not None:
        (workspace / "output.json").write_text(json.dumps(answer, indent=2) + "\n", encoding="utf-8")
    usage = (result or {}).get("modelUsage")
    return report(status, started, exit_code=exit_code, final=reply or reason, cost=(result or {}).get("total_cost_usd"),
                  model=next(iter(usage), None) if isinstance(usage, dict) and usage else None)


if __name__ == "__main__":
    sys.exit(main())
