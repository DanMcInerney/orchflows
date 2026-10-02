"""Load a package: suite.json and tasks/<id>/ with validation, profile selection and the run plan."""
from __future__ import annotations

import json
import math
import re
import tempfile
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import shapes, stage

TASK_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*$")
GRACE_SECONDS = 5.0
VERIFIER_SECONDS = 60.0


class SuiteError(Exception):
    """The package cannot run; `problems` lists everything wrong with it."""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("\n".join(self.problems))


@dataclass(frozen=True)
class Task:
    id: str
    dir: Path
    family: str
    source_group: str
    split: str
    anchor: bool
    smoke: bool
    quick: bool
    weight: float | None
    agent_seconds: float
    verifier_seconds: float
    meta: dict = field(default_factory=dict, compare=False)


@dataclass
class Suite:
    root: Path
    name: str
    repeats: int
    concurrency: int
    deadline_seconds: float | None
    attempt_seconds_estimate: float | None
    attempt_cost_estimate_usd: float | None
    retry_budget: int
    launch_budget: int | None
    grace: float
    provision: list
    observe: list
    primary: str
    tasks: dict[str, Task]
    raw: dict = field(default_factory=dict, compare=False)


def _json(path: Path, problems: list):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        problems.append(f"{path.name}: not found")
    except (OSError, ValueError) as error:
        problems.append(f"{path.name}: {error}")


def _task(folder: Path, problems: list) -> Task | None:
    where = f"tasks/{folder.name}"
    before = len(problems)
    for needed in ("instruction.md", "task.toml", "solution/solve.py", "tests/verify.py"):
        if not (folder / needed).is_file():
            problems.append(f"{where}: missing {needed}")
    doc = None
    if (folder / "task.toml").is_file():
        try:
            doc = tomllib.loads((folder / "task.toml").read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            problems.append(f"{where}/task.toml: {error}")
        else:
            problems += shapes.task_problems(doc, f"{where}/task.toml")
    if (folder / "instruction.md").is_file() and not (folder / "instruction.md").read_text(encoding="utf-8").strip():
        problems.append(f"{where}: instruction.md is empty")
    if len(problems) > before or doc is None:
        return None
    meta = doc["metadata"]
    return Task(folder.name, folder, meta["family"], meta["source_group"], meta["split"], bool(meta.get("anchor", False)),
                bool(meta.get("smoke", False)), bool(meta.get("quick", False)), meta.get("weight"),
                float(doc["agent"]["timeout_sec"]), float(doc.get("verifier", {}).get("timeout_sec", VERIFIER_SECONDS)), doc)


def _tasks(root: Path, problems: list) -> dict[str, Task]:
    folder = root / "tasks"
    if not folder.is_dir():
        problems.append("tasks/: not found")
        return {}
    found = {}
    for entry in sorted(folder.iterdir(), key=lambda item: item.name):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if not TASK_ID.match(entry.name):
            problems.append(f"tasks/{entry.name}: task ids use letters, digits, '.', '_' and '-'")
            continue
        task = _task(entry, problems)
        if task:
            found[task.id] = task
    if not found and not problems:
        problems.append("tasks/: holds no task")
    return found


def read(root: Path) -> tuple[Suite | None, list[str]]:
    """The suite and every problem found; the suite is None when any problem exists."""
    root, problems = Path(root), []
    raw = _json(root / "suite.json", problems)
    if raw is not None:
        problems += shapes.suite_problems(raw)
    tasks = _tasks(root, problems)
    if tasks:
        problems += shapes.weights_problems({t.id: t.weight for t in tasks.values()})
        for profile in ("smoke", "quick"):
            if not any(getattr(t, profile) for t in tasks.values()):
                problems.append(f"no task is flagged {profile} = true, so the {profile} profile is empty")
    if problems:
        return None, problems
    metrics = raw.get("metrics") or {}
    return Suite(root, raw["name"], raw["repeats"], raw["concurrency"], raw.get("deadline_seconds"),
                 raw.get("attempt_seconds_estimate"), raw.get("attempt_cost_estimate_usd"),
                 raw.get("transient_retry_budget", 0), raw.get("launch_budget"),
                 float(raw["grace_seconds"]) if raw.get("grace_seconds") is not None else GRACE_SECONDS,
                 raw.get("provision", []), raw.get("observe", []), metrics.get("primary", "full_success_rate"),
                 tasks, raw), []


def load(root: Path) -> Suite:
    suite, problems = read(root)
    if problems:
        raise SuiteError(problems)
    return suite


def select(suite: Suite, profile: str, only: list[str] | None = None, split: str | None = None) -> list[Task]:
    """The profile's tasks in id order: those flagged smoke or quick, or all. `only` names tasks instead.
    `split` keeps the tasks of that split (development or held-out) from either selection."""
    if profile not in shapes.PROFILES:
        raise SuiteError([f"unknown profile {profile!r}"])
    if split is not None and split not in shapes.SPLITS:
        raise SuiteError([f"unknown split {split!r}; the splits are {', '.join(shapes.SPLITS)}"])
    if only:
        unknown = [name for name in only if name not in suite.tasks]
        if unknown:
            raise SuiteError([f"unknown task {name!r}" for name in unknown])
        chosen = [suite.tasks[name] for name in sorted(set(only))]
    else:
        chosen = [task for task in suite.tasks.values() if profile == "full" or getattr(task, profile)]
    return [task for task in chosen if split is None or task.split == split]


def repeats_for(suite: Suite, profile: str, override: int | None = None) -> int:
    if override is not None:
        if override < 1:
            raise SuiteError(["repeats must be at least 1"])
        return override
    return suite.repeats if profile == "full" else 1


def attempt_cap(suite: Suite, task: Task) -> float:
    """The most seconds one attempt can hold a worker: the solver's limit, the grace period and the verifier's limit."""
    return task.agent_seconds + suite.grace + task.verifier_seconds


def task_meta(tasks: list[Task]) -> dict[str, dict]:
    """The per-task metadata that `aggregate.summarize` reads. Declared weights are renormalized to sum to 1 over
    the tasks a run selects, so a smoke or quick subset still averages as its tasks' weights say."""
    total = math.fsum(t.weight for t in tasks if t.weight is not None)
    weighted = total > 0 and all(t.weight is not None for t in tasks)
    return {t.id: {"family": t.family, "source_group": t.source_group, "split": t.split, "anchor": t.anchor,
                   **({"weight": t.weight / total} if weighted else {})} for t in tasks}


def staging_problems(tasks: list[Task]) -> list[str]:
    """Stage every task into a scratch area; each refusal is a leak the solver would otherwise see."""
    found = []
    with tempfile.TemporaryDirectory(prefix="benchkit-stage-") as scratch:
        for task in tasks:
            try:
                stage.stage_public(task.dir, Path(scratch) / task.id / "workspace", Path(scratch) / task.id / "prompt.md")
            except stage.StagingError as error:
                found.append(f"tasks/{task.id}: staging refused: {error}")
    return found


def plan(suite: Suite, tasks: list[Task], repeats: int, *, jobs: int, deadline: float | None) -> dict:
    """What a run would do: attempts, caps, estimated and worst-case wall time, estimated spend."""
    planned = len(tasks) * repeats
    caps = {task.id: attempt_cap(suite, task) for task in tasks}
    budget = suite.launch_budget if suite.launch_budget is not None else planned + suite.retry_budget
    est = suite.attempt_seconds_estimate
    worst = (sum(cap * repeats for cap in caps.values()) + suite.retry_budget * max(caps.values())) / jobs + max(caps.values())
    cost = suite.attempt_cost_estimate_usd
    return {"tasks": [task.id for task in tasks], "repeats": repeats, "planned_attempts": planned, "jobs": jobs,
            "attempt_caps_seconds": caps, "deadline_seconds": deadline, "launch_budget": budget,
            "transient_retry_budget": suite.retry_budget,
            "estimated_wall_seconds": None if est is None else math.ceil(planned / jobs) * est,
            "wall_upper_bound_seconds": worst if deadline is None else min(worst, deadline),
            "estimated_spend_usd": None if cost is None else planned * cost}
