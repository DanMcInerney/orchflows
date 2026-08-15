#!/usr/bin/env python3
"""Run the suite under every locally installed interpreter CI uses.

A local green covers one of nine CI cells -- one OS, one interpreter --
and AGENTS.md calls it provisional for that reason. Two of the three
axes are closable before a push and this closes one of them: the
interpreter. What is left uncovered is named in the summary rather than
left to be discovered by a runner four minutes later.

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
VERSION_RE = re.compile(r"(\d+)\.(\d+)")


def ci_minors():
    """The interpreter versions CI runs, straight out of the workflow."""

    try:
        found = MATRIX_RE.search(WORKFLOW.read_text(encoding="utf-8"))
    except OSError:
        return ()
    if not found:
        return ()
    return tuple(
        "%s.%s" % pair for pair in VERSION_RE.findall(found.group(1))
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


def discover_interpreters():
    """One interpreter per minor version, this one always included.

    uv's inventory when uv is present, plus the obvious names on PATH.
    Nothing is downloaded: an absent version is reported as uncovered,
    which is true and cheap, rather than fetched behind the user's back
    on what is meant to be a fast local check.
    """

    candidates = [sys.executable]
    candidates.extend(uv_candidates())
    candidates.extend("python" + minor for minor in ci_minors())

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
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(directory, name)
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

    if args.python:
        chosen = {}
        for executable in args.python:
            minor = minor_of(executable)
            if minor is None:
                raise SystemExit("preflight: not a working interpreter: " + executable)
            chosen[minor] = executable
    else:
        installed = discover_interpreters()
        wanted = set(ci_minors()) | {minor_of(sys.executable)}
        # A minor CI does not run buys no cell, and every interpreter here
        # costs another full suite: 3.12 being installed is not a reason to
        # run under it. The running interpreter stays in regardless, so
        # preflight still does something if the workflow cannot be read.
        chosen = {k: v for k, v in installed.items() if k in wanted}
    if not chosen:
        raise SystemExit("preflight: found no interpreters to run")

    required = ci_minors()
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
    print("OS cells covered locally: 1 of 3 -- windows and linux stay CI's")
    if failed:
        print("FAILED: " + ", ".join("python " + r["minor"] for r in failed))
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
