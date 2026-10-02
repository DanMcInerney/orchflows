"""Run one command under a wall cap and stop everything it started.

Output goes to files, never pipes: a pipe held open by a leftover grandchild blocks its reader
(bpo-37424). On Windows the root starts suspended, joins a kill-on-close job object and only then runs, so
no descendant can start outside the job. On POSIX the root leads its own session and process group.
"""
from __future__ import annotations

import os
import signal
import subprocess
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

POLL_SECONDS = 0.05


@dataclass
class Outcome:
    status: str          # completed | timeout | error | canceled; completed means exit code 0
    exit_code: int | None
    seconds: float
    started: float       # wall clock (time.time), for overlap reporting
    finished: float
    left_running: bool   # descendants were alive after the root exited (now stopped)
    reason: str


if os.name == "nt":
    import ctypes

    KERNEL = ctypes.WinDLL("kernel32", use_last_error=True)
    NTDLL = ctypes.WinDLL("ntdll")
    _VOID, _INT, _UINT = ctypes.c_void_p, ctypes.c_int, ctypes.c_uint32
    for _name, _args, _result in (
        ("CreateJobObjectW", [_VOID, ctypes.c_wchar_p], _VOID),
        ("SetInformationJobObject", [_VOID, _INT, _VOID, _UINT], _INT),
        ("OpenProcess", [_UINT, _INT, _UINT], _VOID),
        ("AssignProcessToJobObject", [_VOID, _VOID], _INT),
        ("QueryInformationJobObject", [_VOID, _INT, _VOID, _UINT, _VOID], _INT),
        ("QueryFullProcessImageNameW", [_VOID, _UINT, ctypes.c_wchar_p, ctypes.POINTER(_UINT)], _INT),
        ("TerminateJobObject", [_VOID, _UINT], _INT),
        ("CloseHandle", [_VOID], _INT),
        ("CreateToolhelp32Snapshot", [_UINT, _UINT], _VOID),
        ("Thread32First", [_VOID, _VOID], _INT),
        ("Thread32Next", [_VOID, _VOID], _INT),
        ("OpenThread", [_UINT, _INT, _UINT], _VOID),
        ("ResumeThread", [_VOID], _UINT),
    ):
        getattr(KERNEL, _name).argtypes, getattr(KERNEL, _name).restype = _args, _result
    NTDLL.NtResumeProcess.argtypes, NTDLL.NtResumeProcess.restype = [_VOID], ctypes.c_long

    class _BasicLimits(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", _UINT), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", _UINT),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", _UINT), ("SchedulingClass", _UINT)]

    class _ExtendedLimits(ctypes.Structure):
        _fields_ = [("Basic", _BasicLimits), ("IoCounters", ctypes.c_uint64 * 6),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    class _Members(ctypes.Structure):
        """JOBOBJECT_BASIC_PROCESS_ID_LIST with room for 1024 processes."""
        _fields_ = [("assigned", _UINT), ("listed", _UINT), ("pids", ctypes.c_size_t * 1024)]

    class _ThreadEntry(ctypes.Structure):
        _fields_ = [(name, _UINT) for name in ("size", "usage", "thread_id", "owner_id", "base", "delta", "flags")]

    def _error():
        return ctypes.WinError(ctypes.get_last_error())

    def _resume_threads(pid):
        """Resume every thread of a process; the fallback when NtResumeProcess is refused."""
        snapshot = KERNEL.CreateToolhelp32Snapshot(0x4, 0)  # TH32CS_SNAPTHREAD
        if snapshot in (None, ctypes.c_void_p(-1).value):
            raise _error()
        entry, resumed = _ThreadEntry(), 0
        entry.size = ctypes.sizeof(entry)
        try:
            more = KERNEL.Thread32First(snapshot, ctypes.byref(entry))
            while more:
                if entry.owner_id == pid:
                    thread = KERNEL.OpenThread(0x0002, False, entry.thread_id)  # THREAD_SUSPEND_RESUME
                    if thread:
                        resumed += KERNEL.ResumeThread(thread) != 0xFFFFFFFF
                        KERNEL.CloseHandle(thread)
                more = KERNEL.Thread32Next(snapshot, ctypes.byref(entry))
        finally:
            KERNEL.CloseHandle(snapshot)
        if not resumed:
            raise OSError(f"no thread of process {pid} could be resumed")

    def _ignorable(pid):
        """True for a console host, which briefly outlives its exited client when the harness has no
        console of its own, and for a process already gone."""
        handle = KERNEL.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return ctypes.get_last_error() != 5  # ERROR_ACCESS_DENIED: alive but unreadable
        name, size = ctypes.create_unicode_buffer(1024), _UINT(1024)
        named = KERNEL.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(size))
        KERNEL.CloseHandle(handle)
        return bool(named) and name.value.lower().endswith("\\conhost.exe")


class _JobTree:
    """Windows: the root joins a job before it executes, so descendants inherit it."""

    def __init__(self, grace):
        self.grace, self.proc, self.job = grace, None, KERNEL.CreateJobObjectW(None, None)
        if not self.job:
            raise _error()
        limits = _ExtendedLimits()
        limits.Basic.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not KERNEL.SetInformationJobObject(self.job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = _error()
            self.close()
            raise error

    def start(self, command, **streams):
        self.proc = subprocess.Popen(command, creationflags=0x4 | 0x200, **streams)  # SUSPENDED | NEW_PROCESS_GROUP
        try:
            handle = KERNEL.OpenProcess(0x0100 | 0x0001 | 0x0800 | 0x1000, False, self.proc.pid)
            if not handle:
                raise _error()
            try:
                if not KERNEL.AssignProcessToJobObject(self.job, handle):
                    raise _error()
                if NTDLL.NtResumeProcess(handle) < 0:
                    _resume_threads(self.proc.pid)
            finally:
                KERNEL.CloseHandle(handle)
        except BaseException:
            self.proc.kill()
            self.proc.wait()
            raise
        return self.proc

    def _alive(self):
        """Any job member other than the root and console hosts, including members the list had no room for."""
        members = _Members()
        if not KERNEL.QueryInformationJobObject(self.job, 3, ctypes.byref(members), ctypes.sizeof(members), None):
            return False
        pids = [pid for pid in members.pids[:members.listed] if pid != self.proc.pid]
        return members.assigned > members.listed or any(not _ignorable(pid) for pid in pids)

    def leftovers(self):
        """Stop what the root left running after it exited; True when anything was."""
        found = self._alive()
        if found:
            self.kill()
        return found

    def kill(self):
        KERNEL.TerminateJobObject(self.job, 1)
        try:
            self.proc.wait(self.grace)
        except subprocess.TimeoutExpired:
            pass
        end = time.monotonic() + self.grace
        while self._alive() and time.monotonic() < end:
            time.sleep(POLL_SECONDS)

    def close(self):
        if self.job:
            KERNEL.CloseHandle(self.job)
            self.job = None


class _GroupTree:
    """POSIX: the root leads a session whose process group holds every descendant that stays in it.

    A descendant that starts its own session (setsid) leaves the group, survives the kill and is not reported;
    the standard library offers no portable way to find it again (INTERFACE.md states the limit).
    """

    def __init__(self, grace):
        self.grace, self.proc = grace, None

    def start(self, command, **streams):
        self.proc = subprocess.Popen(command, start_new_session=True, **streams)
        return self.proc

    def _signal(self, number):
        try:
            os.killpg(self.proc.pid, number)
            return True
        except (ProcessLookupError, PermissionError):
            return False

    def leftovers(self):
        found = self._signal(0)
        if found:
            self._signal(signal.SIGKILL)
        return found

    def kill(self):
        self._signal(signal.SIGTERM)
        try:
            self.proc.wait(self.grace)
        except subprocess.TimeoutExpired:
            pass
        self._signal(signal.SIGKILL)
        self.proc.wait()

    def close(self):
        pass


@contextmanager
def _stdin(data):
    if data is None:
        yield subprocess.DEVNULL
        return
    with tempfile.TemporaryFile() as source:
        source.write(data)
        source.seek(0)
        yield source


def _wait(proc, limit, cancel):
    """'exited', 'canceled' or 'timeout', whichever comes first."""
    while True:
        if proc.poll() is not None:
            return "exited"
        if cancel is not None and cancel.is_set():
            return "canceled"
        left = limit - time.monotonic()
        if left <= 0:
            return "timeout"
        try:
            proc.wait(min(POLL_SECONDS, left))
        except subprocess.TimeoutExpired:
            pass


def run_capped(command: list[str], *, cwd: Path, env: dict | None = None, stdout: Path, stderr: Path,
               stdin: bytes | None = None, timeout: float, cancel: threading.Event | None = None,
               grace: float = 5.0) -> Outcome:
    """Run `command` for at most `timeout` seconds; a timeout, a cancel or Ctrl-C stops the whole tree.

    Output lands in the `stdout` and `stderr` files. A launch failure is an 'error' outcome, not an exception.
    """
    stdout, stderr = Path(stdout), Path(stderr)
    for path in (stdout, stderr):
        path.parent.mkdir(parents=True, exist_ok=True)
    clock = time.time()
    tree = None
    with open(stdout, "wb") as out, open(stderr, "wb") as err, _stdin(stdin) as source:
        try:
            tree = (_JobTree if os.name == "nt" else _GroupTree)(grace)
            proc = tree.start([str(part) for part in command], cwd=cwd, env=env, stdin=source, stdout=out, stderr=err)
        except Exception as error:
            if tree:
                tree.close()
            return Outcome("error", None, 0.0, clock, time.time(), False, f"launch failed: {type(error).__name__}: {error}")
        began, started = time.monotonic(), time.time()
        try:
            how = _wait(proc, began + timeout, cancel)
            seconds, finished = time.monotonic() - began, time.time()
            left = tree.leftovers() if how == "exited" else False
            if how != "exited":
                tree.kill()
        except BaseException:
            tree.kill()
            raise
        finally:
            tree.close()
    if how == "canceled":
        return Outcome("canceled", proc.returncode, seconds, started, finished, False, "canceled")
    if how == "timeout":
        return Outcome("timeout", proc.returncode, seconds, started, finished, False, f"exceeded the {timeout:g} s cap")
    reason = "" if proc.returncode == 0 else f"exit code {proc.returncode}"
    if left:
        reason = (reason + "; " if reason else "") + "stopped processes left running after exit"
    return Outcome("completed" if proc.returncode == 0 else "error", proc.returncode, seconds, started, finished, left, reason)
