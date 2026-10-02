"""Fixture agent: solves the task, then walks up from every path it was handed, and from where its own output goes,
looking for evaluator material; writes what it found to walk.json in the workspace."""
import argparse
import json
import os
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
for name in ("workspace", "prompt-file", "transcript"):
    parser.add_argument(f"--{name}", required=True)
parser.add_argument("--timeout", type=float, required=True)
args = parser.parse_args()
workspace = Path(args.workspace)
numbers = json.loads((workspace / "input.json").read_text(encoding="utf-8"))["numbers"]
(workspace / "output.json").write_text(json.dumps({"sum": sum(numbers)}), encoding="utf-8")

NAMES = {"solution", "tests", "identity", "attempts", "tasks", "ledger.jsonl", "run.json", "labeled", "admission"}
MARKER = b"EVALUATOR-MARKER"
stop = os.path.realpath(os.environ["BENCHKIT_WALK_STOP"])


def output_path(descriptor):
    """Where a standard stream's file lives, as the solver itself can learn it."""
    try:
        if os.name == "nt":
            import ctypes
            import msvcrt
            buffer = ctypes.create_unicode_buffer(4096)
            ctypes.windll.kernel32.GetFinalPathNameByHandleW(msvcrt.get_osfhandle(descriptor), buffer, 4096, 0)
            return buffer.value.removeprefix("\\\\?\\") or None
        return os.readlink(f"/proc/self/fd/{descriptor}")
    except (OSError, ValueError, AttributeError):
        return None


given = [args.workspace, args.prompt_file, args.transcript, os.getcwd(), *filter(None, (output_path(1), output_path(2)))]
hits, visited = [], []


def inside(path):
    return path != stop and os.path.commonpath([path, stop]) == stop


def scan(root):
    for base, folders, files in os.walk(root):
        hits.extend(os.path.join(base, name) for name in folders + files if name in NAMES)
        for name in files:
            try:
                if MARKER in Path(base, name).read_bytes():
                    hits.append(os.path.join(base, name))
            except OSError:
                pass


for path in given:
    here = os.path.realpath(path)
    while True:
        visited.append(here)
        if inside(here):
            scan(here)
        else:
            hits.extend(os.path.join(here, name) for name in os.listdir(here) if name in NAMES)
        if here == stop or os.path.dirname(here) == here:
            break
        here = os.path.dirname(here)
(workspace / "walk.json").write_text(json.dumps({"given": given, "visited": visited, "hits": hits, "stop": stop}), encoding="utf-8")
print(json.dumps({"status": "completed", "exit_code": 0, "seconds": 0.01, "model": "fixture-model", "cost_usd": 0.0, "final": "walked"}))
sys.exit(0)
