"""Mutants: known-bad edits of an assembled reference package, each of which the meta-verifier must catch.

`apply(name, package, meta)` edits a package in place. The verifier and solver edits wrap the original script (it
stays beside the wrapper as `verify_base.py` / `solve_base.py`) so one operator works on any domain; the domain
specific parts (the shape of a deliverable) sit in `SHIFT`. The detection each mutant must trigger is checked in
`selfvalidate`.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import registry


class MutationError(Exception):
    pass


HEAD = '''import json
import runpy
import shutil
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent
FLAG = sys.argv.index("--workspace") + 1
WORKSPACE = Path(sys.argv[FLAG])
SUCCESS = {"grading_status": "scored", "full_success": True, "credit": 1.0, "critical_failures": [],
           "dimensions": {"valid": {"credit": 1.0, "weight": 1.0, "required": True}}, "reason": "mutant"}
HALF = {**SUCCESS, "credit": 0.5, "dimensions": {"valid": {"credit": 0.5, "weight": 1.0, "required": True}}}
MINUTES, LINES = 15, 7


def move(text, sign):
    return (datetime.fromisoformat(text.replace("Z", "+00:00")) + timedelta(minutes=MINUTES * sign)).isoformat()


def shift(doc, sign):
    """The deliverable moved a little: a slot 15 minutes, a line range 7 lines, a booking 15 minutes."""
    kind = CONFIG["kind"]
    try:
        if kind == "scheduling" and isinstance(doc.get("start"), str):
            doc["start"], doc["end"] = move(doc["start"], sign), move(doc["end"], sign)
        elif kind == "logtriage" and isinstance(doc.get("failure_lines"), list):
            doc["failure_lines"] = [line + sign * LINES for line in doc["failure_lines"]]
        elif kind == "calendar" and isinstance(doc.get("booked"), dict):
            doc["booked"]["start"], doc["booked"]["end"] = move(doc["booked"]["start"], sign), move(doc["booked"]["end"], sign)
    except (TypeError, ValueError, KeyError):
        pass
    return doc


def load(path):
    try:
        return json.loads(Path(path).read_bytes().decode("utf-8-sig"))
    except (OSError, ValueError):
        return None


def dump(path, doc):
    Path(path).write_text(json.dumps(doc), encoding="utf-8")
'''
VERIFY_HEAD = '''
args = sys.argv[1:]
TASK, RESULT = Path(args[args.index("--task") + 1]), Path(args[args.index("--result") + 1])


def base(task=None, workspace=None):
    task = Path(task or TASK)
    sys.argv = [str(task / "tests" / "verify_base.py"), "--task", str(task), "--workspace", str(workspace or WORKSPACE),
                "--result", str(RESULT)]
    try:
        runpy.run_path(sys.argv[0], run_name="__main__")
    except SystemExit as stop:
        return stop.code or 0
    return 0


def present(name):
    path = WORKSPACE / name
    return path.is_file() and path.stat().st_size > 0
'''
SOLVE_HEAD = '''
def base(task=None, workspace=None):
    task = Path(task or TASK_DIR)
    sys.argv = [str(task / "solution" / "solve_base.py"), "--workspace", str(workspace or WORKSPACE)]
    try:
        runpy.run_path(sys.argv[0], run_name="__main__")
    except SystemExit as stop:
        return stop.code or 0
    return 0
'''

VERIFY_BODIES = {
    "accepts_empty": '''
def main():
    if not present(CONFIG["output"]):
        dump(RESULT, SUCCESS)
        return 0
    return base()
''',
    "flat_grader": '''
def main():
    if present(CONFIG["output"]):
        dump(RESULT, HALF)
        return 0
    return base()
''',
    "in_place_grading": '''
def main():
    reward = WORKSPACE / "reward.txt"
    if reward.is_file() and reward.read_text(encoding="utf-8", errors="replace").strip() == "1":
        dump(RESULT, SUCCESS)
        return 0
    return base()
''',
    "shuffled_labels": '''
def main():
    return base(task=TASK.parent / CONFIG["key"])
''',
    "wrong_key": '''
def main():
    with tempfile.TemporaryDirectory() as scratch:
        copy = Path(scratch) / "workspace"
        shutil.copytree(WORKSPACE, copy)
        doc = load(copy / CONFIG["output"])
        if isinstance(doc, dict):
            dump(copy / CONFIG["output"], shift(doc, -1))
        return base(workspace=copy)
''',
}
SOLVE_BODIES = {
    "broken_reference": '''
def main():
    code = base()
    doc = load(WORKSPACE / CONFIG["output"])
    if isinstance(doc, dict):
        dump(WORKSPACE / CONFIG["output"], shift(doc, 1))
    return code
''',
    "wrong_key": '''
def main():
    code = base()
    doc = load(WORKSPACE / CONFIG["output"])
    if isinstance(doc, dict):
        dump(WORKSPACE / CONFIG["output"], shift(doc, 1))
    return code
''',
    "shuffled_labels": '''
def main():
    other = TASK_DIR.parent / CONFIG["key"]
    for entry in list(WORKSPACE.iterdir()):
        shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
    shutil.copytree(other / "environment", WORKSPACE, dirs_exist_ok=True)
    return base(task=other)
''',
    "hang": '''
def main():
    time.sleep(10 ** 6)
    return 0
''',
}


def task_dirs(package: Path) -> list[Path]:
    return sorted(path for path in (Path(package) / "tasks").iterdir() if path.is_dir())


def wrap(script: Path, head: str, body: str, config: dict) -> None:
    """Replace `script` with a wrapper that runs `body`; the original stays as <stem>_base.py."""
    base = script.with_name(f"{script.stem}_base.py")
    if base.exists():
        raise MutationError(f"{script} is already wrapped")
    script.rename(base)
    text = HEAD + head + f"\nCONFIG = json.loads({json.dumps(json.dumps(config))})\n" + body + "\n\nsys.exit(main())\n"
    script.write_text(text, encoding="utf-8", newline="\n")


def kind_of(meta: registry.MetaTask) -> dict:
    return {"kind": meta.domain, "output": meta.io["output"]}


def patch_verify(package: Path, meta, name: str, only=None, extra=None) -> None:
    for index, task in enumerate(task_dirs(package)):
        if only is None or only(index):
            config = {**kind_of(meta), **(extra(task, index, task_dirs(package)) if extra else {})}
            wrap(task / "tests" / "verify.py", VERIFY_HEAD, VERIFY_BODIES[name], config)


def patch_solve(package: Path, meta, name: str, body: str | None = None, only=None, extra=None) -> None:
    for index, task in enumerate(task_dirs(package)):
        if only is None or only(index):
            config = {**kind_of(meta), **(extra(task, index, task_dirs(package)) if extra else {})}
            wrap(task / "solution" / "solve.py", SOLVE_HEAD, body or SOLVE_BODIES[name], config)


def next_task(task: Path, index: int, tasks: list[Path]) -> dict:
    return {"key": tasks[(index + 1) % len(tasks)].name}


def odd(index: int) -> bool:
    return index % 2 == 1


# ---------------------------------------------------------------- operators

def accepts_empty(package: Path, meta) -> None:
    patch_verify(package, meta, "accepts_empty")


def flat_grader(package: Path, meta) -> None:
    patch_verify(package, meta, "flat_grader")


def in_place_grading(package: Path, meta) -> None:
    patch_verify(package, meta, "in_place_grading")


def broken_reference(package: Path, meta) -> None:
    patch_solve(package, meta, "broken_reference")


def wrong_key(package: Path, meta) -> None:
    patch_verify(package, meta, "wrong_key", only=odd)
    patch_solve(package, meta, "wrong_key", only=odd)


def shuffled_labels(package: Path, meta) -> None:
    patch_verify(package, meta, "shuffled_labels", extra=next_task)
    patch_solve(package, meta, "shuffled_labels", extra=next_task)


def _run_reference(task: Path) -> dict[str, bytes]:
    """The files the task's reference solution writes into a copy of its environment."""
    with tempfile.TemporaryDirectory(prefix="mutant-") as scratch:
        workspace = Path(scratch) / "workspace"
        shutil.copytree(task / "environment", workspace)
        done = subprocess.run([sys.executable, str(task / "solution" / "solve.py"), "--workspace", str(workspace)],
                              capture_output=True, timeout=120)
        if done.returncode != 0:
            raise MutationError(f"{task.name}: the reference solution failed: {done.stderr.decode('utf-8', 'replace')[-300:]}")
        return {path.relative_to(workspace).as_posix(): path.read_bytes() for path in workspace.rglob("*") if path.is_file()}


def answers_reachable(package: Path, meta) -> None:
    """The expected answer sits in the staged environment where a solver can read it."""
    output = meta.io["output"]
    for task in task_dirs(package):
        answer = _run_reference(task).get(output)
        if answer is None:
            raise MutationError(f"{task.name}: the reference wrote no {output}")
        target = task / "environment" / ".cache" / "expected.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(answer)


def _lines(text: str) -> list[str]:
    return re.findall(r"[^\r\n]*(?:\r\n|\n|\r)|[^\r\n]+", text)


def _trivial_scheduling(task: Path) -> None:
    path = task / "environment" / "input.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    first = {**doc["participants"][0], "busy": [], "required": True}
    doc.update(participants=[first], rooms=[], constraints=[], preference="any")
    path.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")


def _trivial_logtriage(task: Path) -> None:
    """Keep one line of context and end the log on the marked failure."""
    expected_path, log_path = task / "tests" / "expected.json", task / "environment" / "build.log"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    first, last = expected["spans"][0]
    lines = _lines(log_path.read_bytes().decode("utf-8", errors="replace"))
    start = max(0, first - 1 - 1)
    log_path.write_bytes("".join(lines[start:last]).encode("utf-8"))
    expected["spans"] = [[first - start, last - start]]
    expected_path.write_text(json.dumps(expected, indent=1) + "\n", encoding="utf-8")


def _trivial_calendar(task: Path) -> None:
    env = task / "environment"
    request = json.loads((env / "request.json").read_text(encoding="utf-8"))
    keep = request["attendees"][0]
    request.update(attendees=[keep], preference="any", priority="normal")
    request.pop("optional", None)
    (env / "request.json").write_text(json.dumps(request, indent=1) + "\n", encoding="utf-8")
    for path in (env / "calendars").glob("*.json"):
        if path.stem != keep:
            path.unlink()
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["events"] = []
        path.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    shutil.rmtree(env / "rooms", ignore_errors=True)
    (env / "policy.json").write_text('{"rules": []}\n', encoding="utf-8")
    if (env / "policy.md").is_file():
        (env / "policy.md").write_text("# Scheduling policy\n\nNo rules apply.\n", encoding="utf-8")


TRIVIAL = {"scheduling": _trivial_scheduling, "logtriage": _trivial_logtriage, "calendar": _trivial_calendar}


def trivial_tasks(package: Path, meta) -> None:
    """Every second task becomes one that needs no work: a lone participant with nothing in the way, a log that
    ends on its failure, a booking for one empty calendar."""
    for index, task in enumerate(task_dirs(package)):
        if odd(index):
            TRIVIAL[meta.domain](task)


def _edit_card(package: Path, claims: list[dict], keep: bool) -> None:
    path = Path(package) / "card.json"
    card = json.loads(path.read_text(encoding="utf-8"))
    card["claims"] = [*(card.get("claims") or [] if keep else []), *claims]
    path.write_text(json.dumps(card, indent=1) + "\n", encoding="utf-8")


def fabricated_card(package: Path, meta) -> None:
    """Claims headroom (a no-op system that sometimes succeeds) and a separation the wrong way round."""
    _edit_card(package, [
        {"id": "f1", "type": "interval", "metric": "full_success_rate", "system": "noop", "low": 0.5, "high": 0.8, "level": 0.9},
        {"id": "f2", "type": "order", "higher": "noop", "lower": "reference", "metric": "mean_credit", "resolved": True}],
        keep=True)


def vacuous_card(package: Path, meta) -> None:
    """Only claims that exclude nothing."""
    _edit_card(package, [
        {"id": "v1", "type": "interval", "metric": "full_success_rate", "system": system, "low": 0.0, "high": 1.0, "level": 0.9}
        for system in ("reference", "noop")], keep=False)


def _replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise MutationError(f"{path.name} has no {old!r} to edit; the kit changed under this mutant")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


SUMMARY_TAIL = '''

_write_outputs_real = write_outputs


def write_outputs(out, suite, info):
    summary = _write_outputs_real(out, suite, info)
    path = Path(out) / "attempts.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    kept = rows[::2]
    for row in kept:
        if row.get("grading_status") == "scored":
            row["full_success"], row["credit"] = True, 1.0
    path.write_text("".join(json.dumps(row) + "\\n" for row in kept), encoding="utf-8")
    summary["overall"]["mean_credit"], summary["overall"]["full_success_rate"] = 1.0, 1.0
    write_json(Path(out) / "summary.json", summary)
    return summary
'''


def summary_mismatch(package: Path, meta) -> None:
    """The runner keeps every other attempt row, reports full counts and writes full credit."""
    records = Path(package) / "benchkit" / "records.py"
    records.write_text(records.read_text(encoding="utf-8").rstrip("\n") + SUMMARY_TAIL, encoding="utf-8", newline="\n")


def no_cap(package: Path, meta) -> None:
    """The runner never stops a solver, and the first task's reference solution never returns."""
    _replace(Path(package) / "benchkit" / "adapters.py", "timeout=task.agent_seconds + grace,", "timeout=10 ** 9,")
    patch_solve(package, meta, "hang", only=lambda index: index == 0)


@dataclass(frozen=True)
class Mutant:
    name: str
    edit: str
    apply: Callable[[Path, registry.MetaTask], None]
    alone: bool = False   # needs a quiet machine and a short meta-verifier cap


MUTANTS: dict[str, Mutant] = {m.name: m for m in (
    Mutant("accepts_empty", "the verifier gives full credit to a missing or empty deliverable", accepts_empty),
    Mutant("answers_reachable", "the expected answer is staged in environment/.cache/expected.json", answers_reachable),
    Mutant("broken_reference", "the reference solution writes a wrong answer", broken_reference),
    Mutant("wrong_key", "on every second task the verifier's key is moved and the reference moved with it", wrong_key),
    Mutant("shuffled_labels", "task i is graded and solved as task i+1", shuffled_labels),
    Mutant("trivial_tasks", "every second task is replaced by one that needs no work", trivial_tasks),
    Mutant("flat_grader", "the verifier gives credit 0.5 and full success to any non-empty deliverable", flat_grader),
    Mutant("fabricated_card", "the card adds a no-op success claim and a no-op-over-reference order claim", fabricated_card),
    Mutant("vacuous_card", "the card holds only [0, 1] interval claims", vacuous_card),
    Mutant("summary_mismatch", "the runner drops every other attempt row, reports full counts and full credit", summary_mismatch),
    Mutant("in_place_grading", "the verifier reads reward.txt from the workspace", in_place_grading),
    Mutant("no_cap", "the runner ignores timeouts and the first reference solution hangs", no_cap, alone=True),
)}
QUICK = ("accepts_empty", "summary_mismatch", "flat_grader")


def apply(name: str, package: Path, meta: registry.MetaTask) -> Mutant:
    mutant = MUTANTS[name]
    mutant.apply(Path(package), meta)
    return mutant
