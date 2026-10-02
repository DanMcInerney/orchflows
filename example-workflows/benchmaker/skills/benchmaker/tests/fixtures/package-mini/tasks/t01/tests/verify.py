"""Verifier: output.json must hold the expected sum; credit is half for a numeric sum, half for the right one."""
import argparse
import json
from pathlib import Path

W_VALID = 0.5

parser = argparse.ArgumentParser()
parser.add_argument("--task", required=True)
parser.add_argument("--workspace", required=True)
parser.add_argument("--result", required=True)
args = parser.parse_args()
expected = json.loads((Path(args.task) / "tests" / "expected.json").read_text(encoding="utf-8"))["sum"]
valid = correct = 0.0
try:
    value = json.loads((Path(args.workspace) / "output.json").read_text(encoding="utf-8"))["sum"]
    valid = 1.0 if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0
    correct = 1.0 if valid and value == expected else 0.0
except (OSError, ValueError, KeyError, TypeError):
    pass
result = {"grading_status": "scored", "full_success": correct == 1.0, "credit": W_VALID * valid + (1 - W_VALID) * correct,
          "dimensions": {"valid": {"credit": valid, "weight": W_VALID, "required": True},
                         "correct": {"credit": correct, "weight": 1 - W_VALID, "required": True}},
          "critical_failures": [], "reason": ""}
Path(args.result).write_text(json.dumps(result), encoding="utf-8")
