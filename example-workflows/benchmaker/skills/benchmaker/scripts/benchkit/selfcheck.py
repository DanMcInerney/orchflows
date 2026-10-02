"""Checks that the harness itself behaves on this machine, in a few seconds: run before trusting a benchmark.

Each check exercises the kit's real mechanics on throwaway fixtures and no model: concurrency, the process cap,
retries, a crashing verifier, interrupt and resume, changed-byte refusal and the staging leak refusal.
"""
from __future__ import annotations

import json
import platform
import sys
import tempfile
import threading
import time
from pathlib import Path

from . import adapters, identity, stage
from .launch import run_capped
from .schedule import Ledger, Unit, run_units
from .suite import Task

TREE = ("import subprocess, sys, time\n"
        "subprocess.Popen([sys.executable, '-c', 'import sys, time; time.sleep(1.0); open(sys.argv[1], \"w\").write(\"x\")', sys.argv[1]])\n"
        "time.sleep(60)\n")


class Failed(Exception):
    pass


def _expect(condition, detail):
    if not condition:
        raise Failed(detail)


def _units(count):
    return [Unit(f"u{n}/1", f"u{n}", 1) for n in range(1, count + 1)]


def overlap(tmp: Path) -> str:
    def attempt(unit, retry, cancel):
        out = run_capped([sys.executable, "-c", "import time; time.sleep(0.6)"], cwd=tmp, stdout=tmp / f"{unit.task}.out",
                         stderr=tmp / f"{unit.task}.err", timeout=10, cancel=cancel)
        return {"status": "completed" if out.status == "completed" else "infrastructure-error", "reason": out.reason}

    stats = run_units(_units(2), attempt, ledger=Ledger(tmp / "ledger.jsonl"), jobs=2, attempt_cap=10)
    _expect(stats.by_status == {"completed": 2}, f"units ended {stats.by_status}")
    _expect(stats.achieved_overlap >= 1.5, f"two 0.6 s attempts at jobs=2 overlapped only {stats.achieved_overlap:.2f}x")
    return f"achieved overlap {stats.achieved_overlap:.2f}x at jobs=2"


def timeout_reaps_tree(tmp: Path) -> str:
    marker, script = tmp / "marker", tmp / "tree.py"
    script.write_text(TREE, encoding="utf-8")
    outcome = run_capped([sys.executable, str(script), str(marker)], cwd=tmp, stdout=tmp / "out", stderr=tmp / "err", timeout=0.4)
    _expect(outcome.status == "timeout", f"the capped run ended {outcome.status}")
    time.sleep(1.4)
    _expect(not marker.exists(), "a grandchild outlived the cap and wrote its marker")
    return "a grandchild started at launch was stopped with its parent"


def transient_retry(tmp: Path) -> str:
    def run(budget):
        calls = []

        def attempt(unit, retry, cancel):
            calls.append(retry)
            return {"status": "infrastructure-error" if retry == 0 else "completed", "transient": retry == 0}

        stats = run_units(_units(1), attempt, ledger=Ledger(tmp / f"ledger-{budget}.jsonl"), jobs=1,
                          transient=lambda result: result.get("transient") is True, retry_budget=budget)
        return calls, stats

    calls, stats = run(1)
    _expect(calls == [0, 1] and stats.retries == 1 and stats.by_status == {"completed": 1}, f"with budget 1: calls {calls}")
    calls, stats = run(0)
    _expect(calls == [0] and stats.by_status == {"infrastructure-error": 1}, f"with budget 0: calls {calls}")
    return "a transient failure retried once within budget 1 and not at all within budget 0"


def verifier_crash(tmp: Path) -> str:
    folder = tmp / "tasks" / "t01"
    (folder / "tests").mkdir(parents=True)
    (folder / "tests" / "verify.py").write_text("raise SystemExit('crashed on purpose')\n", encoding="utf-8")
    (tmp / "workspace").mkdir()
    task = Task("t01", folder, "f", "g", "development", False, False, False, None, 5.0, 10.0)
    grade = adapters.verify(task, tmp / "workspace", tmp / "log")
    _expect(grade["grading_status"] == "unscored" and grade["reason"], f"a crashing verifier graded {grade['grading_status']}")
    return "a crashing verifier left the attempt unscored with a reason"


def interrupt_and_resume(tmp: Path) -> str:
    calls, lock = [], threading.Lock()

    def attempt(unit, retry, cancel):
        with lock:
            calls.append((unit.key, retry))
        if unit.key == "u2/1" and retry == 0:
            raise KeyboardInterrupt
        return {"status": "completed"}

    ledger = Ledger(tmp / "ledger.jsonl")
    first = run_units(_units(3), attempt, ledger=ledger, jobs=1)
    _expect(first.stopped == "interrupt", f"the interrupted run stopped as {first.stopped!r}")
    second = run_units(_units(3), attempt, ledger=ledger, jobs=1)
    _expect(second.by_status == {"completed": 3}, f"the resumed run ended {second.by_status}")
    finished = sorted(row["key"] for row in ledger.records() if row["kind"] == "finished" and row["status"] == "completed")
    _expect(finished == ["u1/1", "u2/1", "u3/1"], f"completed units were recorded as {finished}")
    _expect(sorted(calls) == [("u1/1", 0), ("u2/1", 0), ("u2/1", 1), ("u3/1", 0)], f"attempt calls were {sorted(calls)}")
    return "the resumed run relaunched only the interrupted unit; no completed unit ran twice"


def changed_bytes(tmp: Path) -> str:
    source = tmp / "tasks"
    (source / "t01").mkdir(parents=True)
    (source / "t01" / "instruction.md").write_text("add them\n", encoding="utf-8")
    identity.retain({"tasks": source}, tmp / "kept")
    try:
        _expect(identity.compare({"tasks": source}, tmp / "kept") == [], "unchanged bytes were reported as changed")
        (source / "t01" / "instruction.md").write_text("add them!\n", encoding="utf-8")
        found = identity.compare({"tasks": source}, tmp / "kept")
        _expect(found == ["changed: tasks/t01/instruction.md"], f"one changed byte was reported as {found}")
    finally:
        identity.discard(tmp / "kept")
    return "one changed byte was found by comparison with the retained copy"


def staging_leak(tmp: Path) -> str:
    folder = tmp / "package" / "tasks" / "t01"
    (folder / "tests").mkdir(parents=True)
    (folder / "environment").mkdir()
    (folder / "instruction.md").write_text("solve it\n", encoding="utf-8")
    (folder / "tests" / "expected.json").write_text('{"answer": 42}\n', encoding="utf-8")
    (folder / "environment" / "notes.json").write_text('{"answer": 42}\n', encoding="utf-8")
    try:
        stage.stage_public(folder, tmp / "workspace", tmp / "prompt.md")
    except stage.StagingError as error:
        _expect("byte-identical" in str(error), f"the leak was refused for another reason: {error}")
        return "an environment file that copies a test file was refused"
    raise Failed("an environment file identical to a test file was staged")


CHECKS = (("overlap", overlap), ("timeout-reaps-process-tree", timeout_reaps_tree), ("transient-retry", transient_retry),
          ("verifier-crash-unscored", verifier_crash), ("interrupt-and-resume", interrupt_and_resume),
          ("changed-bytes-detected", changed_bytes), ("staging-leak-refused", staging_leak))


def run(tmp: Path | None = None) -> dict:
    """Run every check in its own folder under `tmp`; `passed` is false, with the reason, for any that fails."""
    own = tmp is None
    tmp = Path(tempfile.mkdtemp(prefix="benchkit-selfcheck-")) if own else Path(tmp)
    results = []
    for name, check in CHECKS:
        folder = tmp / name
        folder.mkdir(parents=True, exist_ok=True)
        try:
            results.append({"name": name, "passed": True, "detail": check(folder)})
        except Failed as failure:
            results.append({"name": name, "passed": False, "detail": str(failure)})
        except Exception as error:  # a harness defect is a failed check, not a crash of the checker
            results.append({"name": name, "passed": False, "detail": f"{type(error).__name__}: {error}"})
    if own:
        identity.discard(tmp)
    return {"platform": platform.platform(), "python": platform.python_version(), "checks": results}


if __name__ == "__main__":
    report = run()
    print(json.dumps(report, indent=2))
    sys.exit(0 if all(check["passed"] for check in report["checks"]) else 1)
