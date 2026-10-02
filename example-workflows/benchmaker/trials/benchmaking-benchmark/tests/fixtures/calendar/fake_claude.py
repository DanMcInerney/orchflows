"""A stand-in for the Claude CLI in tests: no model is called.

It reads the prompt from stdin, takes the scenario from the first line (`scenario: NAME`), records what it was
given in agent-ran.json in its working directory, and prints stream-json events of the shape `claude -p
--output-format stream-json --verbose` produces.
"""
import json
import sys
import time
from pathlib import Path

prompt = sys.stdin.read()
scenario = prompt.splitlines()[0].split(":", 1)[1].strip() if prompt.startswith("scenario:") else "ok"
Path("agent-ran.json").write_text(json.dumps({"argv": sys.argv[1:], "prompt": prompt, "cwd": str(Path.cwd())}), encoding="utf-8")

MODEL = "claude-haiku-4-5-20251001"


def emit(event):
    print(json.dumps(event), flush=True)


def result(**fields):
    emit({"type": "result", "subtype": "success", "is_error": False, "result": "Booked the meeting.", "total_cost_usd": 0.0123,
          "num_turns": 4, "stop_reason": "end_turn", "modelUsage": {MODEL: {"inputTokens": 1}}, **fields})


if scenario == "sleep":
    time.sleep(60)
elif scenario == "crash":
    print("claude: something broke", file=sys.stderr)
    sys.exit(1)
else:
    emit({"type": "system", "subtype": "init", "model": MODEL, "plugins": [{"name": "booking-rules", "path": "x"}], "tools": ["Read", "Skill"]})
    print("not json: a stray line", flush=True)
    emit({"type": "assistant", "message": {"content": [{"type": "text", "text": "Loading the skill."},
                                                       {"type": "tool_use", "name": "Skill", "input": {"skill": "booking-rules"}},
                                                       {"type": "tool_use", "name": "Read", "input": {"file_path": "request.json"}}]}})
    if scenario == "limit":
        result(is_error=True, result="You've hit your session limit · resets 4pm", api_error_status=429)
        sys.exit(1)
    elif scenario == "throttled":
        result(is_error=True, result="Request was rejected.", api_error_status=429)
        sys.exit(1)
    elif scenario == "refusal":
        result(stop_reason="refusal", result="I can't help with that.")
    elif scenario == "cutoff":
        result(stop_reason="max_tokens")
    else:
        result()
