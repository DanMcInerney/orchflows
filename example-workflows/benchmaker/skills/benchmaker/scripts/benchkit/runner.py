"""Execute a profile into a run directory: stage, solve, capture, grade, and keep the ledger.

The live workspace of an attempt, and every path a solver is handed (prompt, transcript, and the files its output
lands in), exist only in a temporary root outside the package and the output directory; the solver files join the
attempt record once its tree is gone. The final workspace is captured after that, and verifiers grade a copy.
"""
from __future__ import annotations

import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from . import adapters, aggregate, identity, records, stage, stopping
from . import suite as suites
from .schedule import OPEN_STATUSES, Ledger, OwnerLock, RunStats, Unit, run_units
from .suite import Suite, Task

OK, HARNESS, REFUSED, STOPPED, INTERRUPTED = 0, 1, 2, 3, 4
EXIT_FOR = {"": OK, "deadline": STOPPED, "launch-budget": STOPPED, "stop-on": INTERRUPTED, "interrupt": INTERRUPTED}
STATE_FOR = {"": "complete", "deadline": "deadline", "launch-budget": "launch-budget", "stop-on": "usage-limit",
             "interrupt": "interrupted"}
EARLY = "stopped early"


class Refused(Exception):
    """The run may not start or continue; the message says why (exit code 2)."""


@dataclass
class Result:
    code: int
    state: str
    summary: dict


def _inside(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def sources(suite: Suite, agent: adapters.Agent, names: list[str] | None = None) -> dict[str, Path]:
    """The files whose bytes identify a run: the suite, tasks, adapters, runner, kit and the agent directory."""
    wanted = {"suite.json": suite.root / "suite.json", "tasks": suite.root / "tasks", "adapters": suite.root / "adapters",
              "run.py": suite.root / "run.py", "benchkit": suite.root / "benchkit"}
    if agent.path:
        wanted["agent"] = agent.path
    return {name: path for name, path in wanted.items() if (name in names if names is not None else path.exists())}


class Run:
    def __init__(self, suite: Suite, out: Path, agent: adapters.Agent, info: dict):
        self.suite, self.out, self.agent, self.info = suite, out, agent, info
        self.tasks = [suite.tasks[name] for name in info["tasks"]]
        self.by_id = {task.id: task for task in self.tasks}
        self.ledger = Ledger(out / "ledger.jsonl")

    def _rel(self, path: Path) -> str:
        return path.relative_to(self.out).as_posix()

    def cap(self, unit: Unit) -> float:
        return suites.attempt_cap(self.suite, self.by_id[unit.task])

    def _keep(self, task: Task, handed: Path, folder: Path) -> None:
        """Put the prompt and the solver's transcript and output files in the attempt record. The prompt is copied
        from the task, not from the folder the solver could write to; links and folders the solver left are dropped."""
        try:
            if (handed / "prompt.md").exists():
                shutil.copyfile(task.dir / "instruction.md", folder / "prompt.md")
            for name in ("transcript.jsonl", "stdout.txt", "stderr.txt"):
                path = handed / name
                if path.is_file() and not stage.is_link(path):
                    shutil.move(str(path), str(folder / name))
        except OSError:
            pass

    def attempt(self, unit: Unit, retry: int, cancel) -> dict:
        """One launch: stage, solve, capture, and grade when the status is a scored one. Returns the attempt row."""
        task = self.by_id[unit.task]
        folder = self.out / "attempts" / task.id / f"{unit.repeat}-{retry}"
        stage.discard(folder)  # whatever a launch the ledger lost left behind
        folder.mkdir(parents=True)
        row = records.blank_row(task.id, unit.repeat, retry)
        scratch = Path(tempfile.mkdtemp(prefix="benchkit-"))
        handed, captured = scratch / "solver", folder / "workspace"
        try:
            try:
                stage.stage_public(task.dir, scratch / "workspace", handed / "prompt.md")
            except stage.StagingError as error:
                return {**row, "status": "infrastructure-error", "reason": f"staging refused: {error}",
                        "grade_reason": "not graded: infrastructure-error"}
            solved = adapters.solve(self.agent, task, scratch / "workspace", handed, grace=self.suite.grace, cancel=cancel)
            skipped = stage.capture(scratch / "workspace", captured)
        finally:
            self._keep(task, handed, folder)
            stage.discard(scratch)
        solved["capture_skipped"] = skipped
        records.write_json(folder / "solver.json", solved)
        row.update(status=solved["status"], reason=solved["reason"], started=records.iso(solved["started"]),
                   finished=records.iso(solved["finished"]), seconds=round(solved["seconds"], 3),
                   exit_code=solved["exit_code"], model=solved["model"], cost_usd=solved["cost_usd"],
                   left_running=solved["left_running"], workspace=self._rel(captured),
                   transcript=self._rel(folder / "transcript.jsonl") if (folder / "transcript.jsonl").exists() else None,
                   transient=solved["transient"], usage_limit=solved["usage_limit"], capture_skipped=skipped)
        if solved["status"] in aggregate.SCORED:
            grade = adapters.grade_copy(task, captured, folder)
            records.write_json(folder / "grade.json", grade)
            row.update({name: grade[name] for name in records.GRADE_FIELDS}, grade_reason=grade["reason"],
                       grading_seconds=round(grade["seconds"], 3))
            self.ledger.append("graded", key=unit.key, retry=retry, grading_status=grade["grading_status"],
                               reason=grade["reason"])
        else:
            row["grade_reason"] = f"not graded: {solved['status']}"
        return row

    def dispatch(self, units: list[Unit], jobs: int, deadline: float | None) -> RunStats:
        return run_units(units, self.attempt, ledger=self.ledger, jobs=jobs, deadline=deadline, attempt_cap=self.cap,
                         transient=lambda result: result.get("transient") is True, retry_budget=self.suite.retry_budget,
                         launch_budget=self.suite.launch_budget, stop_on=lambda result: result.get("usage_limit") is True)

    def _verdict(self, task: Task, repeat: int) -> str | None:
        """'below', 'above' or 'inside' once the task's earlier repeats settle it against the stop band."""
        low, high, level = self.info["stop_band"]
        rows = [row for row in records.attempt_rows(self.ledger.records()) if row["task"] == task.id and row["repeat"] < repeat]
        metrics = aggregate.task_metrics(rows, repeat - 1)
        if not metrics["scored"]:
            return None
        verdict = stopping.decide(metrics["passed"], metrics["scored"], low=low, high=high, level=level,
                                  max_attempts=self.info["repeats"])
        return verdict if verdict in ("below", "above", "inside") else None

    def _skip(self, task: Task, first: int, verdict: str) -> None:
        """Record the repeats a settled task will not run, once; each is a not-launched unit with the reason."""
        low, high, level = self.info["stop_band"]
        reason = f"{EARLY}: {verdict} the band [{low:g}, {high:g}] at level {level:g}"
        rows = self.ledger.records()
        for repeat in range(first, self.info["repeats"] + 1):
            key = f"{task.id}/{repeat}"
            last = [row for row in rows if row["kind"] == "finished" and row["key"] == key]
            if last and (last[-1]["status"] not in OPEN_STATUSES or last[-1].get("reason") == reason):
                continue
            retry = max((row["retry"] for row in rows if row["kind"] == "launched" and row["key"] == key), default=-1) + 1
            self.ledger.append("finished", key=key, retry=retry, status="not-launched", reason=reason)

    def execute(self, jobs: int, deadline: float | None) -> list[RunStats]:
        repeats = self.info["repeats"]
        units = [Unit(f"{task.id}/{repeat}", task.id, repeat) for repeat in range(1, repeats + 1) for task in self.tasks]
        if not self.info["stop_band"]:
            return [self.dispatch(units, jobs, deadline)]
        planned = {row["key"] for row in self.ledger.records() if row["kind"] == "planned"}
        for unit in units:
            if unit.key not in planned:
                self.ledger.append("planned", key=unit.key, task=unit.task, repeat=unit.repeat)
        began, parts = time.monotonic(), []
        for repeat in range(1, repeats + 1):
            live = []
            for task in self.tasks:
                verdict = self._verdict(task, repeat)
                if verdict:
                    self._skip(task, repeat, verdict)
                else:
                    live.append(Unit(f"{task.id}/{repeat}", task.id, repeat))
            if not live:
                break
            left = None if deadline is None else max(0.0, deadline - (time.monotonic() - began))
            parts.append(self.dispatch(live, jobs, left))
            if parts[-1].stopped:
                break
        return parts

    def go(self, jobs: int, deadline: float | None, setup_seconds: float) -> Result:
        """Run what is left, then rebuild attempts.jsonl and summary.json. The outputs are written even when the
        run raises, so an interrupted or failed run is never left without them."""
        began, clock, parts, failed = time.time(), time.monotonic(), [], True
        try:
            parts = self.execute(jobs, deadline)
            failed = False
        finally:
            stopped = next((part.stopped for part in parts if part.stopped), "")
            self.info["invocations"].append({
                "started": records.iso(began), "finished": records.iso(time.time()), "stopped": stopped,
                "wall_seconds": round(time.monotonic() - clock, 3), "setup_seconds": round(setup_seconds, 3),
                "launched": sum(part.launched for part in parts), "jobs": jobs, "deadline_seconds": deadline})
            self.info.update(finished=records.iso(time.time()), state="failed" if failed else STATE_FOR[stopped])
            records.write_json(self.out / "run.json", self.info)
            summary = records.write_outputs(self.out, self.suite, self.info)
        return Result(EXIT_FOR[stopped], STATE_FOR[stopped], summary)


def start(suite: Suite, out: Path, spec: str, *, profile: str, repeats: int | None = None, jobs: int | None = None,
          deadline: float | None = None, only: list[str] | None = None, split: str | None = None,
          stop_band: tuple[float, float, float] | None = None) -> Result:
    """Begin a run of `profile` with the agent `spec` in a new output directory; `split` keeps one split's tasks."""
    began = time.monotonic()
    tasks = suites.select(suite, profile, only, split)
    if not tasks:
        raise Refused(f"no task is selected: the {profile} profile" + (f" with the {split} split" if split else "")
                      + (" and the named tasks" if only else "") + " matches none")
    agent = adapters.resolve(spec, suite.root)
    repeats = suites.repeats_for(suite, profile, repeats)
    jobs = jobs or suite.concurrency
    if jobs < 1:
        raise Refused("jobs must be at least 1")
    out = Path(out).resolve()
    if out.exists() and any(out.iterdir()):
        raise Refused(f"{out} is not empty; resume continues a run, or choose another output directory")
    held = sources(suite, agent)
    for name in ("tasks", "adapters", "benchkit", "agent"):
        if name in held and _inside(out, held[name].resolve()):
            raise Refused(f"the output directory {out} lies inside {name}")
    scratch = Path(tempfile.gettempdir()).resolve()
    if _inside(scratch, out) or _inside(scratch, suite.root.resolve()):
        raise Refused(f"the temporary root {scratch} lies inside the output directory or the package")
    leaks = suites.staging_problems(tasks)
    if leaks:
        raise Refused("\n".join(leaks))
    with OwnerLock(out):
        observed = identity.observe(suite.observe, suite.root)
        identity.retain(held, out / "identity")
        info = {"profile": profile, "split": split, "agent": spec, "agent_path": str(agent.path) if agent.path else None,
                "repeats": repeats, "jobs": jobs, "tasks": [task.id for task in tasks],
                "stop_band": list(stop_band) if stop_band else None, "retained": sorted(held),
                "observed_versions": observed, "started": records.iso(time.time()), "finished": None,
                "state": "running", "invocations": []}
        records.write_json(out / "run.json", info)
        return Run(suite, out, agent, info).go(jobs, deadline if deadline is not None else suite.deadline_seconds,
                                               time.monotonic() - began)


def resume(suite: Suite, out: Path, *, jobs: int | None = None, deadline: float | None = None) -> Result:
    """Continue a run from its ledger once the retained bytes and the observed versions match."""
    began = time.monotonic()
    out = Path(out).resolve()
    try:
        info = records.read_run(out)
    except (OSError, ValueError):
        raise Refused(f"{out} has no readable run.json; it is not a run directory") from None
    with OwnerLock(out):
        agent = adapters.resolve(info["agent_path"] or info["agent"], suite.root)
        changed = identity.compare(sources(suite, agent, info["retained"]), out / "identity")
        observed = identity.observe(suite.observe, suite.root)
        recorded = info["observed_versions"]
        changed += [f"observed {name}: {recorded.get(name)!r} then, {observed.get(name)!r} now"
                    for name in sorted(set(recorded) | set(observed)) if recorded.get(name) != observed.get(name)]
        if changed:
            raise Refused("changed since the run began:\n  " + "\n  ".join(changed))
        missing = [name for name in info["tasks"] if name not in suite.tasks]
        if missing:
            raise Refused(f"tasks no longer in the package: {', '.join(missing)}")
        expected = {f"{task}/{repeat}" for task in info["tasks"] for repeat in range(1, info["repeats"] + 1)}
        foreign = sorted({row["key"] for row in Ledger(out / "ledger.jsonl").records() if "key" in row} - expected)
        if foreign:
            raise Refused(f"the ledger has records for units this run never planned: {', '.join(foreign)}")
        jobs = jobs or info["jobs"]
        info["jobs"], info["state"] = jobs, "running"
        return Run(suite, out, agent, info).go(jobs, deadline if deadline is not None else suite.deadline_seconds,
                                               time.monotonic() - began)
