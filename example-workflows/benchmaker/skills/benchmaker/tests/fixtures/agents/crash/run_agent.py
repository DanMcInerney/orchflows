"""Fixture agent: crashes without printing a protocol line."""
import argparse
import json
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
for name in ("workspace", "prompt-file", "transcript"):
    parser.add_argument(f"--{name}", required=True)
parser.add_argument("--timeout", type=float, required=True)
args = parser.parse_args()
workspace = Path(args.workspace)
assert Path(args.prompt_file).read_text(encoding="utf-8").strip(), "the prompt file is empty"


def solve(offset=0):
    numbers = json.loads((workspace / "input.json").read_text(encoding="utf-8"))["numbers"]
    (workspace / "output.json").write_text(json.dumps({"sum": sum(numbers) + offset}), encoding="utf-8")
    Path(args.transcript).write_text(json.dumps({"event": "wrote output.json"}) + "\n", encoding="utf-8")


def report(status, code=0, **extra):
    print(json.dumps({"status": status, "exit_code": code, "seconds": 0.01, "model": "fixture-model", "cost_usd": 0.01,
                      "final": extra.pop("final", status), **extra}))
    sys.exit(code)


raise RuntimeError("crashed on purpose")
