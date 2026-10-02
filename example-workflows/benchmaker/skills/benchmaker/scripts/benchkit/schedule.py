"""Bounded, resumable execution of independent units. The ledger is the only record of what ran.

A unit is `task/repeat`. Each launch is recorded before dispatch and each result after it, so a crashed run
shows exactly which launches have no known result and a resumed run never repeats finished work.
"""
from __future__ import annotations

import json
import os
import socket
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

POLL_SECONDS = 0.05
KINDS = {"planned", "launched", "finished", "graded", "note"}
OPEN_STATUSES = {"interrupted", "canceled", "not-launched"}   # a resumed run attempts these units again
INTERRUPTED = "no completion record; remote completion or billing uncertain"
REFUSALS = {"deadline": "an attempt cap would pass the deadline", "launch-budget": "launch budget spent",
            "stop-on": "admission stopped by an earlier result", "interrupt": "run interrupted",
            "retry-budget": "retry budget spent"}
_BINARY = getattr(os, "O_BINARY", 0)


class LedgerError(Exception):
    pass


class Busy(Exception):
    pass


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class Ledger:
    """Append-only JSONL. Every append is flushed to disk; kinds: planned, launched, finished, graded, note."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()

    def append(self, kind: str, **fields) -> dict:
        if kind not in KINDS:
            raise ValueError(f"unknown ledger kind {kind!r}")
        record = {"kind": kind, "at": _now(), **fields}
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._repair()
            self._write(record)
        return record

    def _write(self, record):
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | _BINARY)
        try:
            os.write(fd, (json.dumps(record, default=str) + "\n").encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)

    def _repair(self):
        """Make the file end at a line boundary before appending; a torn final line is dropped with a note."""
        if not self.path.exists() or not self.path.stat().st_size:
            return
        with open(self.path, "rb") as file:
            file.seek(-1, os.SEEK_END)
            if file.read(1) == b"\n":
                return
        data = self.path.read_bytes()
        keep = data.rfind(b"\n") + 1
        tail = data[keep:]
        try:
            json.loads(tail.decode("utf-8"))
        except ValueError:
            with open(self.path, "r+b") as file:
                file.truncate(keep)
            self._write({"kind": "note", "at": _now(), "message": "dropped a torn final line",
                         "dropped": tail.decode("utf-8", "replace")})
        else:
            fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | _BINARY)
            try:
                os.write(fd, b"\n")
            finally:
                os.close(fd)

    def records(self) -> list[dict]:
        """Every record in order. A torn final line is ignored and reported as a note; any other bad line raises."""
        if not self.path.exists():
            return []
        lines = self.path.read_bytes().split(b"\n")
        tail = lines.pop()  # empty when the file ends with a newline
        rows = [self._parse(line, number) for number, line in enumerate(lines, 1)]
        if tail:
            try:
                rows.append(self._parse(tail, len(lines) + 1))
            except LedgerError:
                rows.append({"kind": "note", "message": "ignored a torn final line", "dropped": tail.decode("utf-8", "replace")})
        return rows

    def _parse(self, line, number):
        try:
            row = json.loads(line.decode("utf-8"))
        except ValueError:
            row = None
        if not isinstance(row, dict) or row.get("kind") not in KINDS:
            raise LedgerError(f"{self.path}: line {number} is not a ledger record")
        return row


class OwnerLock:
    """One owner per run directory: <run>/OWNER, created exclusively, removed on release."""

    def __init__(self, run: Path):
        self.path = Path(run) / "OWNER"
        self.held = False

    def acquire(self) -> "OwnerLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | _BINARY)
        except FileExistsError:
            try:
                owner = self.path.read_text(encoding="utf-8").strip() or "unreadable"
            except OSError:
                owner = "unreadable"
            raise Busy(f"{self.path} is held by {owner}; remove it only if that process is gone") from None
        with os.fdopen(fd, "wb") as out:
            out.write(json.dumps({"pid": os.getpid(), "host": socket.gethostname(), "started": _now()}).encode("utf-8"))
        self.held = True
        return self

    def release(self):
        if self.held:
            self.held = False
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *_):
        self.release()


@dataclass
class Unit:
    key: str             # "t01/1"
    task: str
    repeat: int
    payload: dict = field(default_factory=dict)


@dataclass
class RunStats:
    planned: int
    launched: int              # launches made by this call
    by_status: dict            # each unit's latest status across the whole run
    retries: int               # transient retries launched by this call
    wall_seconds: float
    attempt_seconds_sum: float
    achieved_overlap: float
    peak: int
    timeline: list             # {"key", "retry", "start", "end", "status"}, offsets in seconds from the call's start
    stopped: str = ""          # deadline | launch-budget | stop-on | interrupt; empty when every unit was admitted


def _states(records):
    """Per unit key: launched rows in order and the latest finished row."""
    launched, finished = {}, {}
    for row in records:
        if row["kind"] == "launched":
            launched.setdefault(row["key"], []).append(row)
        elif row["kind"] == "finished":
            finished[row["key"]] = row
    return launched, finished


def _resume(units, ledger):
    """Plan new units, close launches that have no result, and list what is left to attempt."""
    records = ledger.records()
    planned = {row["key"] for row in records if row["kind"] == "planned"}
    for unit in units:
        if unit.key not in planned:
            ledger.append("planned", key=unit.key, task=unit.task, repeat=unit.repeat)
    launched, _ = _states(records)
    done = {(row["key"], row["retry"]) for row in records if row["kind"] == "finished"}
    for key, rows in launched.items():
        for row in rows:
            if (key, row["retry"]) not in done:
                ledger.append("finished", key=key, retry=row["retry"], status="interrupted", reason=INTERRUPTED)
    records = ledger.records()
    launched, finished = _states(records)
    pending = []
    for unit in units:
        last = finished.get(unit.key)
        if last is None or last["status"] in OPEN_STATUSES:
            rows = launched.get(unit.key, [])
            pending.append((unit, max((row["retry"] for row in rows), default=-1) + 1, "resume" if rows else "first"))
    launches = sum(row["kind"] == "launched" for row in records)
    retries = sum(row["kind"] == "launched" and row.get("cause") == "transient" for row in records)
    return pending, launches, retries


class _Run:
    def __init__(self, attempt, ledger, jobs, deadline, attempt_cap, transient, retry_budget, launch_budget, stop_on):
        self.attempt, self.ledger, self.jobs, self.deadline, self.attempt_cap = attempt, ledger, jobs, deadline, attempt_cap
        self.transient, self.retry_budget, self.launch_budget, self.stop_on = transient, retry_budget, launch_budget, stop_on
        self.lock, self.cancel, self.done = threading.Lock(), threading.Event(), threading.Event()
        self.queue, self.workers = deque(), 0
        self.stopped, self.halted = "", False
        self.launches = self.retries = self.active = self.peak = 0
        self.launched_now = self.retried_now = 0
        self.seconds_sum, self.timeline = 0.0, []
        self.start = time.monotonic()

    def _elapsed(self):
        return time.monotonic() - self.start

    def _refusal(self, unit):
        """Why this unit may not launch, or ''. Called with the lock held."""
        if self.cancel.is_set():
            return self.stopped or "interrupt"
        if self.halted:
            return "stop-on"
        if self.launch_budget is not None and self.launches >= self.launch_budget:
            return "launch-budget"
        cap = self.attempt_cap(unit) if callable(self.attempt_cap) else self.attempt_cap
        if self.deadline is not None and self._elapsed() + cap > self.deadline:
            return "deadline"
        return ""

    def _admit(self, unit, retry, cause):
        """Record the launch, or return the reason it was refused."""
        with self.lock:
            why = self._refusal(unit)
            if not why and cause == "transient" and self.retries >= self.retry_budget:
                why = "retry-budget"
            if why:
                if why != "retry-budget":
                    self.stopped = self.stopped or why
                return why
            self.launches += 1
            self.launched_now += 1
            if cause == "transient":
                self.retries += 1
                self.retried_now += 1
            self.active += 1
            self.peak = max(self.peak, self.active)
        self.ledger.append("launched", key=unit.key, retry=retry, cause=cause)
        return ""

    def _attempt(self, unit, retry):
        began, aborted = self._elapsed(), False
        try:
            result = self.attempt(unit, retry, self.cancel)
        except Exception as error:
            result = {"status": "infrastructure-error", "reason": f"attempt raised {type(error).__name__}: {error}"}
        except BaseException as error:  # an attempt killed from outside: leave the unit for a resumed run
            result = {"status": "interrupted", "reason": f"attempt aborted by {type(error).__name__}"}
            aborted = True
        if not isinstance(result, dict) or not result.get("status"):
            result = {"status": "infrastructure-error", "reason": "attempt returned no status"}
        ended = self._elapsed()
        with self.lock:
            self.active -= 1
            self.seconds_sum += ended - began
            self.timeline.append({"key": unit.key, "retry": retry, "start": round(began, 3), "end": round(ended, 3),
                                  "status": result["status"]})
        self.ledger.append("finished", key=unit.key, retry=retry, status=result["status"],
                           reason=result.get("reason", ""), result=result)
        if aborted:
            self._interrupt()
        elif self.stop_on is not None and self.stop_on(result):
            with self.lock:
                self.halted = True
                self.stopped = self.stopped or "stop-on"
        return result

    def _unit(self, unit, retry, cause):
        while True:
            why = self._admit(unit, retry, cause)
            if why:
                if cause == "transient":
                    self.ledger.append("note", key=unit.key, message=f"retry not launched: {REFUSALS.get(why, why)}")
                else:
                    self.ledger.append("finished", key=unit.key, retry=retry, status="not-launched",
                                       reason=REFUSALS.get(why, why))
                return
            result = self._attempt(unit, retry)
            if not (self.transient and self.transient(result)) or self.cancel.is_set():
                return
            retry, cause = retry + 1, "transient"

    def _work(self):
        try:
            while True:
                with self.lock:
                    if not self.queue:
                        return
                    unit, retry, cause = self.queue.popleft()
                self._unit(unit, retry, cause)
        finally:
            with self.lock:
                self.workers -= 1
                if not self.workers:
                    self.done.set()

    def _interrupt(self):
        with self.lock:
            self.stopped = "interrupt"
        self.cancel.set()

    def _supervise(self, threads):
        """Start the workers and wait for them; the deadline and Ctrl-C cancel what is running, and every
        tree is reaped before this returns, whatever else arrives meanwhile."""
        started = 0
        while True:
            try:
                while started < len(threads):
                    threads[started].start()
                    started += 1
                if self.done.wait(POLL_SECONDS):
                    break
                if self.deadline is not None and self._elapsed() >= self.deadline and not self.cancel.is_set():
                    with self.lock:
                        self.stopped = self.stopped or "deadline"
                    self.cancel.set()
            except KeyboardInterrupt:
                self._interrupt()
        for thread in threads:
            while thread.is_alive():
                try:
                    thread.join(POLL_SECONDS)
                except KeyboardInterrupt:
                    self._interrupt()

    def execute(self, pending, launches, retries):
        self.launches, self.retries = launches, retries
        self.queue.extend(pending)
        threads = [threading.Thread(target=self._work, daemon=True) for _ in range(min(self.jobs, len(pending)))]
        self.workers = len(threads)
        if not threads:
            self.done.set()
        self.start = time.monotonic()
        self._supervise(threads)
        return time.monotonic() - self.start


def run_units(units, attempt, *, ledger, jobs, deadline=None, attempt_cap=0.0, transient=None,
              retry_budget=0, launch_budget=None, stop_on=None) -> RunStats:
    """Run every unit that is not yet finished, `jobs` at a time.

    attempt(unit, retry, cancel) -> result dict with a "status"; it must stop promptly once `cancel` is set.
    deadline is seconds from this call; no unit is admitted when `attempt_cap` (seconds, or a function of the
    unit) would pass it, and when it passes the running attempts are canceled. launch_budget caps launches
    over the whole ledger, and so does retry_budget for retries. transient(result) says a failure may be
    retried; stop_on(result) ends admission. Refused units finish as 'not-launched'; Ctrl-C cancels the
    running attempts and returns with stopped='interrupt'. Units whose result is 'interrupted', 'canceled'
    or 'not-launched' are attempted again by a later call.
    """
    units = list(units)
    if jobs < 1:
        raise ValueError("jobs must be positive")
    if len({unit.key for unit in units}) != len(units):
        raise ValueError("unit keys must be unique")
    pending, launches, retries = _resume(units, ledger)
    run = _Run(attempt, ledger, jobs, deadline, attempt_cap, transient, retry_budget, launch_budget, stop_on)
    wall = run.execute(pending, launches, retries)
    _, finished = _states(ledger.records())
    by_status = {}
    for unit in units:
        status = finished[unit.key]["status"] if unit.key in finished else "not-launched"
        by_status[status] = by_status.get(status, 0) + 1
    run.timeline.sort(key=lambda row: (row["start"], row["key"]))
    return RunStats(len(units), run.launched_now, by_status, run.retried_now, wall, run.seconds_sum,
                    run.seconds_sum / wall if wall else 0.0, run.peak, run.timeline, run.stopped)
