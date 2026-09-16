"""Read-only source preservation and identity check; evidence stays outside candidate."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True

RUN = Path(__file__).resolve().parent.parent
PROJECT = RUN / "project"
TOOL = Path("C:/Users/danhm/.orchflows/artifacts/software-factory-comparison-20260916-01/tools/release_simulator.py")
BASELINE = "19786e961751f9745f8fd92516b7a6e1ba249534"
PRESERVED = ("baseline_reference.py", "TASK.md", "RUN_CONTEXT.md", "tests/test_public.py")
saved_hashes = {Path(row["Path"]).resolve(): row["Hash"].lower()
                for row in json.loads((RUN / "artifacts/preserved-baseline-hashes.json").read_text(encoding="utf-8-sig"))}
for name in PRESERVED:
    if hashlib.sha256((PROJECT / name).read_bytes()).hexdigest() != saved_hashes[(PROJECT / name).resolve()]:
        raise SystemExit(f"Preserved source changed: {name}")
expected_note = "1688056b517941c9189dc5c3d646e967d90f2d26dfc3532eb5764c755a80cd15"
if hashlib.sha256((PROJECT / "caller-note.txt").read_bytes()).hexdigest() != expected_note:
    raise SystemExit("caller-note.txt changed")
spec = importlib.util.spec_from_file_location("release_simulator", TOOL)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
state = {
    "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True).strip(),
    "git_status": subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=PROJECT, text=True),
    "preservation_check": "passed",
    "identity": module.identity(PROJECT),
}
print(json.dumps(state, indent=2))
