#!/usr/bin/env python3
"""Parallel unit-test runner: one test module per child interpreter.

Sharding is by module across *processes*, never threads: the suite
performs whole-interpreter mutations (``install.Path.home``,
``ui.html.escape``, ``Path.open``, ``os.chdir``, ``sys.path``) that make
thread parallelism unsound. Threads here only wait on subprocesses.

Scheduling is longest-first from a duration cache written at
``.orch/run_tests_times.json`` (gitignored runtime state), falling back
to alphabetical when no cache exists. Results stream as modules finish;
a failing module's captured output is reproduced verbatim.

Stdlib only, no network, Python 3.9+, POSIX and Windows.

Usage:
    python tools/run_tests.py [-j N] [-v] [--tests-dir DIR] [MODULE ...]
"""

from __future__ import annotations

import argparse
import html
import inspect
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TESTS_DIR = ROOT / "tests"
CACHE_PATH = ROOT / ".orch" / "run_tests_times.json"


# --- child: run one module in this interpreter ------------------------


def guarded_state() -> dict:
    """Snapshot the process-global seams tests are allowed to borrow only.

    The suite imports ``Path`` through ``install`` and ``html`` through
    ``ui``; guarding their defining objects catches changes through either
    alias without importing those large application modules into every child.
    """

    return {
        "install.Path.home": inspect.getattr_static(Path, "home"),
        "ui.html.escape": html.escape,
        "pathlib.Path.open": inspect.getattr_static(Path, "open"),
        "os.chdir": (os.chdir, os.getcwd()),
        "sys.path": (sys.path, tuple(sys.path)),
    }


def meaningful_sys_path(entries):
    """Drop expired scratch roots, which can no longer affect imports.

    Isolated-tree tests execute copied tools whose lazy imports put that
    temporary tree on ``sys.path``. ``TemporaryDirectory`` removes the tree
    before the module returns; the dead absolute entry is inert in this
    single-purpose child and is not live whole-interpreter residue.
    """

    temp_root = os.path.normcase(os.path.abspath(tempfile.gettempdir()))
    meaningful = []
    for entry in entries:
        try:
            raw = os.fspath(entry)
        except TypeError:
            meaningful.append(entry)
            continue
        absolute = os.path.normcase(os.path.abspath(raw))
        try:
            in_scratch = os.path.commonpath((temp_root, absolute)) == temp_root
        except ValueError:
            in_scratch = False
        if in_scratch and absolute != temp_root and not os.path.exists(absolute):
            continue
        meaningful.append(entry)
    return tuple(meaningful)


def leaked_seams(before: dict):
    """Name every guarded seam whose identity or value escaped a test."""

    leaked = []
    if inspect.getattr_static(Path, "home") is not before["install.Path.home"]:
        leaked.append("install.Path.home")
    if html.escape is not before["ui.html.escape"]:
        leaked.append("ui.html.escape")
    if inspect.getattr_static(Path, "open") is not before["pathlib.Path.open"]:
        leaked.append("pathlib.Path.open")
    chdir, cwd = before["os.chdir"]
    try:
        cwd_leaked = os.getcwd() != cwd
    except OSError:
        cwd_leaked = True
    if os.chdir is not chdir or cwd_leaked:
        leaked.append("os.chdir")
    path_object, path_value = before["sys.path"]
    if (
        sys.path is not path_object
        or meaningful_sys_path(sys.path) != meaningful_sys_path(path_value)
    ):
        leaked.append("sys.path")
    return leaked


def run_child(module: str, import_root: str, result_path: str, verbosity: int) -> int:
    """Run one test module and write its counts to ``result_path``.

    The script's own directory is dropped from ``sys.path`` first: under
    ``unittest discover`` nothing on ``tools/`` is importable by bare
    name, and leaving it there would let a test import a tool module the
    real suite cannot reach.
    """

    script_dir = Path(__file__).resolve().parent
    sys.path[:] = [p for p in sys.path if p and Path(p).resolve() != script_dir]
    sys.path.insert(0, import_root)

    suite = unittest.TestLoader().loadTestsFromName(module)
    before = guarded_state()
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=verbosity).run(suite)
    leaks = leaked_seams(before)
    for seam in leaks:
        sys.stderr.write("leaked whole-interpreter seam: " + seam + "\n")
    payload = {
        "module": module,
        "tests": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors) + len(leaks),
        "skipped": len(result.skipped),
        "unexpected": len(result.unexpectedSuccesses),
        "ok": result.wasSuccessful() and not leaks,
    }
    # A leaked ``Path.open`` must not keep the child from reporting that
    # exact leak. ``open`` is a separate seam and the result path is absolute.
    with open(result_path, "w", encoding="utf-8") as stream:
        stream.write(json.dumps(payload))
    return 0 if payload["ok"] else 1


# --- parent: discovery, scheduling, dispatch --------------------------


def discover(tests_dir: Path):
    """Return (import root, module-name prefix, dotted module names).

    A package directory is imported through its parent so intra-package
    imports (``from tests.baseline_pin import ...``) resolve; a plain
    directory of ``test_*.py`` files is imported as top-level modules.
    """

    if (tests_dir / "__init__.py").is_file():
        import_root, prefix = tests_dir.parent, tests_dir.name + "."
    else:
        import_root, prefix = tests_dir, ""
    # `test*.py` is unittest discover's own default pattern; matching it
    # keeps the two runners over the same module set.
    modules = sorted(prefix + path.stem for path in tests_dir.glob("test*.py"))
    return import_root, prefix, modules


def resolve(selector: str, modules, prefix: str) -> str:
    """Map ``tests/test_x.py``, ``tests.test_x`` or ``test_x`` to a module."""

    name = selector[:-3] if selector.endswith(".py") else selector
    name = name.replace("\\", "/").replace("/", ".").strip(".")
    for candidate in (name, prefix + name):
        if candidate in modules:
            return candidate
    raise SystemExit("run_tests: no such test module: " + selector)


def load_times() -> dict:
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_times(results) -> None:
    """Merge this run's durations into the cache, atomically.

    Merged rather than replaced so a subset run keeps every other
    module's timing; ``os.replace`` so two concurrent runs cannot leave
    a half-written file.
    """

    times = load_times()
    for record in results:
        times[record["module"]] = round(record["duration"], 3)
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        handle, tmp = tempfile.mkstemp(dir=str(CACHE_PATH.parent), suffix=".tmp")
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(times, stream, sort_keys=True, indent=1)
        os.replace(tmp, str(CACHE_PATH))
    except OSError:
        pass  # A timing cache is an optimization; never fail a run for it.


def schedule(modules, times):
    """Longest-first. Untimed modules sort first (unknown cost is the
    risky one to leave for last), which makes an absent cache exactly
    alphabetical order."""

    return sorted(modules, key=lambda name: (-times.get(name, float("inf")), name))


def child_env() -> dict:
    """This process's environment with the child's stdio pinned to UTF-8.

    ``PYTHONIOENCODING`` rather than the interpreter's UTF-8 mode: it moves
    the pipe encoding and nothing else, so a test still sees the filesystem
    and locale behaviour of the platform it is grading.
    """

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def run_module(module: str, import_root: Path, verbosity: int) -> dict:
    handle, result_path = tempfile.mkstemp(prefix="run_tests_", suffix=".json")
    os.close(handle)
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--child",
        module,
        "--import-root",
        str(import_root),
        "--result-file",
        result_path,
        "--child-verbosity",
        str(verbosity),
    ]
    started = time.monotonic()
    # Bytes, not text=True: a child may emit anything, and a decode error
    # in the runner would lose the very output a CI log needs. The child is
    # told to encode its own stdio as UTF-8 so the decode below is faithful
    # rather than lossy: a Windows child otherwise writes its failure text
    # in the console codepage, cp1252, and every non-ASCII character in an
    # assertion message reaches this process as U+FFFD.
    completed = subprocess.run(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=child_env()
    )
    duration = time.monotonic() - started
    output = completed.stdout.decode("utf-8", "replace")
    try:
        record = json.loads(Path(result_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        record = {
            "module": module,
            "tests": 0,
            "failures": 0,
            "errors": 1,
            "skipped": 0,
            "unexpected": 0,
            "ok": False,
            "note": "child wrote no result (exit %d)" % completed.returncode,
        }
    finally:
        try:
            os.unlink(result_path)
        except OSError:
            pass
    record["duration"] = duration
    record["output"] = output
    record["returncode"] = completed.returncode
    return record


# --- reporting --------------------------------------------------------


def detail(record: dict) -> str:
    parts = [
        "%s=%d" % (key, record[key])
        for key in ("failures", "errors", "skipped", "unexpected")
        if record.get(key)
    ]
    if record.get("note"):
        parts.append(record["note"])
    return "  (" + ", ".join(parts) + ")" if parts else ""


def emit(text: str) -> None:
    """Write captured child output to stdout, whatever it holds.

    A failing module's output is the whole reason a CI log is read, and the
    console it lands on is not always UTF-8 -- a Windows runner's is cp1252,
    which cannot encode every character an assertion message may carry.
    Encoding here with ``backslashreplace`` costs one mangled glyph; letting
    ``sys.stdout`` raise costs the report, every module after it, and the
    exit code that says which one failed.
    """

    stream = getattr(sys.stdout, "buffer", None)
    if stream is None:  # a stdout that is not a real file (a captured one)
        sys.stdout.write(text)
        return
    sys.stdout.flush()
    stream.write(text.encode(sys.stdout.encoding or "utf-8", "backslashreplace"))
    stream.flush()


def report(records, wall: float, jobs: int) -> int:
    failed = [record for record in records if not record["ok"]]
    for record in failed:
        print("\n" + "=" * 70)
        print("FAILED MODULE: %s (exit %d)" % (record["module"], record["returncode"]))
        print("=" * 70)
        emit(record["output"])

    totals = {key: sum(r[key] for r in records) for key in ("tests", "failures", "errors", "skipped")}
    print("\n" + "-" * 70)
    print(
        "%d modules, %d tests: %d failures, %d errors, %d skipped"
        % (len(records), totals["tests"], totals["failures"], totals["errors"], totals["skipped"])
    )
    serial = sum(record["duration"] for record in records)
    print("wall %.2fs across %d workers (summed module time %.2fs)" % (wall, jobs, serial))
    print("slowest modules:")
    for record in sorted(records, key=lambda r: -r["duration"])[:5]:
        print("  %7.2fs  %s" % (record["duration"], record["module"]))
    if failed:
        print("FAILED: " + ", ".join(record["module"] for record in failed))
        return 1
    print("OK")
    return 0


# --- entry point ------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_tests.py",
        description="Run the unit suite one module per process.",
        epilog="With no MODULE arguments every tests/test_*.py runs.",
    )
    parser.add_argument("modules", metavar="MODULE", nargs="*", help="module name or path to run")
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=os.cpu_count() or 1,
        help="worker processes (default: CPU count); -j 1 runs modules one at a time in order",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose child test output")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="ignore the duration cache: schedule alphabetically, as a cold checkout does",
    )
    parser.add_argument(
        "--tests-dir", default=str(DEFAULT_TESTS_DIR), help="directory of test_*.py (default: tests/)"
    )
    child = parser.add_argument_group("child mode (internal)")
    child.add_argument("--child", metavar="MODULE", help=argparse.SUPPRESS)
    child.add_argument("--import-root", help=argparse.SUPPRESS)
    child.add_argument("--result-file", help=argparse.SUPPRESS)
    child.add_argument("--child-verbosity", type=int, default=1, help=argparse.SUPPRESS)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.child:
        return run_child(args.child, args.import_root, args.result_file, args.child_verbosity)
    if args.jobs < 1:
        raise SystemExit("run_tests: -j must be at least 1")

    tests_dir = Path(args.tests_dir).resolve()
    if not tests_dir.is_dir():
        raise SystemExit("run_tests: no such directory: " + str(tests_dir))
    import_root, prefix, discovered = discover(tests_dir)
    if not discovered:
        raise SystemExit("run_tests: no test_*.py under " + str(tests_dir))
    selected = (
        [resolve(name, discovered, prefix) for name in args.modules] if args.modules else discovered
    )

    verbosity = 2 if args.verbose else 1
    # The cache is gitignored, so CI always schedules alphabetically while
    # any local checkout that has run once schedules longest-first. Those
    # are different co-schedulings, and a module only races the modules it
    # runs beside: `--no-cache` is how a local run reproduces CI's.
    ordered = schedule(selected, {} if args.no_cache else load_times())
    jobs = min(args.jobs, len(ordered))
    print("running %d modules across %d workers" % (len(ordered), jobs))
    started = time.monotonic()
    records = []

    def finish(record: dict) -> None:
        records.append(record)
        print(
            "%-4s %-42s %5d tests %7.2fs%s"
            % (
                "ok" if record["ok"] else "FAIL",
                record["module"],
                record["tests"],
                record["duration"],
                detail(record),
            ),
            flush=True,
        )

    if jobs == 1:
        for module in ordered:
            finish(run_module(module, import_root, verbosity))
    else:
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = [pool.submit(run_module, module, import_root, verbosity) for module in ordered]
            for future in as_completed(futures):
                finish(future.result())
    wall = time.monotonic() - started

    if tests_dir == DEFAULT_TESTS_DIR.resolve() and not args.no_cache:
        save_times(records)
    return report(records, wall, jobs)


if __name__ == "__main__":
    # Guarded for Windows: any spawn-based re-import of this module must
    # not re-enter main().
    raise SystemExit(main(sys.argv[1:]))
