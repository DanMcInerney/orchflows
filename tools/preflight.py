#!/usr/bin/env python3
"""Run the suite under every locally installed interpreter CI uses.

The matrix has five active CI legs: three Ubuntu, one macOS, and one Windows.
A local green covers at most one OS/interpreter pair, so AGENTS.md calls
it provisional. This closes the interpreter axis before a push; the
summary names what remains uncovered.

The version axis is not hypothetical. `Path.resolve()` on a name holding
a NUL raises through 3.12 and answers a path on 3.13, and the suite
asserted the first as a premise -- green on this host, red on one CI
cell. The OS axis stays CI's: what can be caught statically is caught by
the suite's own invariants (a chdir inside a self-deleting temp tree, a
cleanup that swallows), and the rest needs the platform.

Stdlib only, no network, Python 3.9+, POSIX and Windows.

Usage:
    python tools/preflight.py [-j N] [--python PATH ...] [MODULE ...]
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "tools" / "run_tests.py"
WORKFLOW = ROOT / ".github" / "workflows" / "checks.yml"
# The matrix is read, never restated: a version added to CI must not need a
# second edit here to be preflighted.
MATRIX_RE = re.compile(r"python-version:\s*\[([^\]]*)\]")
OS_MATRIX_RE = re.compile(r"os:\s*\[([^\]]*)\]")
VERSION_RE = re.compile(r"(\d+)\.(\d+)")
# Which OS cell this host is. `sys.platform` and not `os.name`: macOS and
# Linux are one `posix` and CI runs a cell of each. The value is the prefix
# of the matrix's own label, so `windows-latest` moving to `windows-2025`
# needs no edit here.
OS_OF_PLATFORM = {"win32": "windows", "darwin": "macos", "linux": "ubuntu"}


class MatrixUnreadable(RuntimeError):
    """The CI matrix could not be read, so no cell can be called covered."""


def _matrix_axis(pattern, label):
    """One axis of the workflow's matrix, as the text between its brackets."""

    try:
        text = WORKFLOW.read_text(encoding="utf-8")
    except OSError as error:
        raise MatrixUnreadable("cannot read %s: %s" % (WORKFLOW, error))
    found = pattern.search(text)
    if not found:
        raise MatrixUnreadable("no %s axis in %s" % (label, WORKFLOW))
    return found.group(1)


def ci_minors():
    """The interpreter versions CI runs, straight out of the workflow.

    A workflow this cannot read, or a matrix it does not recognise, raises
    rather than answering ``()``. Empty is the answer "CI runs no
    interpreter", and the summary reads it as "cells covered locally: 0 of
    0", prints OK and exits 0 -- full coverage of nothing, reported as
    fact by the one tool whose whole subject is what a local green covers.
    """

    minors = tuple(
        "%s.%s" % pair
        for pair in VERSION_RE.findall(_matrix_axis(MATRIX_RE, "python-version"))
    )
    if not minors:
        raise MatrixUnreadable("the python-version axis in %s names none" % WORKFLOW)
    return minors


def ci_os_cells():
    """The operating systems CI runs, out of the same matrix and by the same rule."""

    cells = tuple(
        cell.strip().strip("'\"")
        for cell in _matrix_axis(OS_MATRIX_RE, "os").split(",")
        if cell.strip()
    )
    if not cells:
        raise MatrixUnreadable("the os axis in %s names none" % WORKFLOW)
    return cells


def os_coverage_line(cells):
    """What this host's own OS cell buys, and which cells stay CI's.

    Hardcoded, this line read "1 of 3 -- windows and linux stay CI's" on a
    Windows host: the cell the run had just covered named among the two it
    had not, and a count restated beside the matrix that decides it.
    """

    here = OS_OF_PLATFORM.get(sys.platform)
    covered = [cell for cell in cells if here and cell.split("-")[0] == here]
    uncovered = [cell for cell in cells if cell not in covered]
    return "OS cells covered locally: %d of %d%s -- %s %s CI's" % (
        len(covered), len(cells),
        (" (%s)" % ", ".join(covered)) if covered else " (%s runs no cell of the matrix)" % sys.platform,
        ", ".join(uncovered), "stays" if len(uncovered) == 1 else "stay",
    )


def minor_of(executable):
    """``(major, minor)`` as the interpreter itself reports it, or None.

    Asked rather than parsed out of the path: `python3` is whatever it is,
    and a preflight that guessed would report a cell it never ran.
    """

    try:
        proc = subprocess.run(
            [executable, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    answer = proc.stdout.decode("utf-8", "replace").strip()
    return answer if proc.returncode == 0 and VERSION_RE.fullmatch(answer) else None


def uv_candidates():
    """Interpreter paths `uv python list --only-installed` reports.

    Its rows are ``<key> <path>`` or ``<key> <path> -> <target>``; the
    path is what is wanted either way, and following the arrow would name
    the same interpreter twice under two paths.
    """

    try:
        proc = subprocess.run(
            ["uv", "python", "list", "--only-installed"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    found = []
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        fields = line.split()
        if len(fields) >= 2:
            found.append(fields[1])
    return found


def discover_interpreters(minors):
    """One interpreter per minor version, this one always included.

    uv's inventory when uv is present, plus the obvious names on PATH for
    each version CI runs. Nothing is downloaded: an absent version is
    reported as uncovered, which is true and cheap, rather than fetched
    behind the user's back on what is meant to be a fast local check.
    """

    candidates = [sys.executable]
    candidates.extend(uv_candidates())
    candidates.extend("python" + minor for minor in minors)

    by_minor = {}
    for candidate in candidates:
        resolved = candidate if os.path.sep in candidate else _which(candidate)
        if not resolved or not os.path.exists(resolved):
            continue
        minor = minor_of(resolved)
        if minor and minor not in by_minor:
            by_minor[minor] = resolved
    return by_minor


def _which(name):
    """The PATH entry ``name`` names, PATHEXT honoured where the host uses it.

    ``python3.13`` on Windows is ``python3.13.exe``, so a bare-name test
    finds nothing, every version CI runs reads as "not installed here" and
    the summary prints that false cause as the reason a cell stays CI's.

    Written out rather than handed to ``shutil.which``, which prepends the
    current directory on Windows: PATH is the whole question here, and an
    interpreter picked up from the tree being checked is not on it.
    """

    suffixes = [""]
    if os.name == "nt":
        suffixes += [
            extension
            for extension in os.environ.get("PATHEXT", "").split(os.pathsep)
            if extension.strip()
        ]
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        for suffix in suffixes:
            candidate = os.path.join(directory, name + suffix)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
    return None


def run_one(minor, executable, jobs, modules):
    command = [executable, str(RUNNER), "--no-cache", "-j", str(jobs)] + list(modules)
    started = time.monotonic()
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return {
        "minor": minor,
        "executable": executable,
        "ok": proc.returncode == 0,
        "duration": time.monotonic() - started,
        "output": proc.stdout.decode("utf-8", "replace"),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="preflight.py",
        description="Run the suite under every locally installed interpreter CI uses.",
    )
    parser.add_argument("modules", metavar="MODULE", nargs="*")
    parser.add_argument("-j", "--jobs", type=int, default=os.cpu_count() or 1,
                        help="total worker processes, split across interpreters")
    parser.add_argument("--python", action="append", default=[], metavar="PATH",
                        help="use this interpreter instead of discovering (repeatable)")
    args = parser.parse_args(argv)

    # Read once and before anything runs: every line this tool prints is a
    # statement about the matrix, so a matrix it cannot read is a refusal
    # rather than a run whose summary has nothing to measure against.
    try:
        required = ci_minors()
        os_cells = ci_os_cells()
    except MatrixUnreadable as failure:
        raise SystemExit("preflight: %s" % failure)

    if args.python:
        chosen = {}
        for executable in args.python:
            minor = minor_of(executable)
            if minor is None:
                raise SystemExit("preflight: not a working interpreter: " + executable)
            chosen[minor] = executable
    else:
        installed = discover_interpreters(required)
        wanted = set(required) | {minor_of(sys.executable)}
        # A minor CI does not run buys no cell, and every interpreter here
        # costs another full suite: 3.12 being installed is not a reason to
        # run under it. The running interpreter stays in regardless, so a
        # host CI's own versions have missed still checks itself.
        chosen = {k: v for k, v in installed.items() if k in wanted}
    if not chosen:
        raise SystemExit("preflight: found no interpreters to run")

    missing = [minor for minor in required if minor not in chosen]
    order = sorted(chosen, key=lambda minor: tuple(int(n) for n in minor.split(".")))
    # Interpreters run together and split the workers between them: the
    # suite's wall clock is one long module, so three of them overlap for
    # roughly the cost of one.
    per = max(2, args.jobs // len(order))
    print("preflight: %d interpreters (%s), %d workers each"
          % (len(order), ", ".join(order), per))
    if missing:
        print("preflight: CI also runs %s -- not installed here, so still CI-only"
              % ", ".join(missing))

    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=len(order)) as pool:
        results = list(pool.map(
            lambda minor: run_one(minor, chosen[minor], per, args.modules), order
        ))
    wall = time.monotonic() - started

    failed = [record for record in results if not record["ok"]]
    for record in failed:
        print("\n" + "=" * 70)
        print("FAILED under python %s (%s)" % (record["minor"], record["executable"]))
        print("=" * 70)
        sys.stdout.write(record["output"])

    print("\n" + "-" * 70)
    for record in results:
        print("%-4s python %-5s %7.2fs  %s"
              % ("ok" if record["ok"] else "FAIL", record["minor"],
                 record["duration"], record["executable"]))
    print("preflight wall %.2fs" % wall)
    covered = [minor for minor in required if minor in chosen]
    print("CI interpreter cells covered locally: %d of %d%s"
          % (len(covered), len(required),
             (" (missing " + ", ".join(missing) + ")") if missing else ""))
    print(os_coverage_line(os_cells))
    if failed:
        print("FAILED: " + ", ".join("python " + r["minor"] for r in failed))
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
