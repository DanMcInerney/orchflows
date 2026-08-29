#!/usr/bin/env python3
"""Process-isolated, module-sharded unit-test runner.

Threads only wait on child interpreters because tests mutate global seams.
Scheduling is longest-first from a gitignored cache, with cold-start priors.
Stdlib only, Python 3.9+, POSIX and Windows.

Usage:
    python tools/run_tests.py [-j N] [-v] [--tests-dir DIR]
        [--scope PATH[,PATH] | MODULE ...]
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

try:  # imported as ``tools.run_tests`` with the repository on sys.path
    from tools import run_tests_scope
except ImportError:  # run as ``python tools/run_tests.py``, tools/ on sys.path
    import run_tests_scope

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TESTS_DIR = ROOT / "tests"
CACHE_PATH = ROOT / ".orch" / "run_tests_times.json"
TIMING_PATH = ROOT / ".orch" / "run_tests_record.json"
# Cold-checkout order: the modules whose *worst* matrix leg is expensive,
# that leg's duration descending. Worst and not typical -- the long pole
# moves by leg (serial_compat on 3.9) and starting a module early costs
# nothing on a leg where it is cheap. Read
# off the timing artifacts CI uploads; a leg with a cache never reads it.
DEFAULT_COLD_ORDER = tuple("tests.test_" + _name for _name in (
    "installer_planning", "workspace", "serial_compat",
    "installer_shared", "cutcheck", "tickets", "validate", "ui",
    "run_required", "affected_tests", "cell_linter",
))
IMPORT_BOOTSTRAP_ROOTS = frozenset(
    os.path.normcase(os.path.abspath(str(ROOT / relative)))
    for relative in (".", "scripts", "benchmarks/benchmaker/tools")
)

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
        "os.environ": (os.environ, dict(os.environ)),
    }

def restore_guarded_state(before: dict) -> list[str]:
    """Restore environment state a module borrowed before its child exits."""
    env_object, env_value = before["os.environ"]
    changed = os.environ is not env_object or dict(os.environ) != env_value
    if changed:
        os.environ = env_object
        os.environ.clear(); os.environ.update(env_value)
    return ["os.environ"] if changed else []

def meaningful_sys_path(entries):
    """Drop dead scratch roots and the exact suite bootstrap roots.

    Scratch is judged strictly outside this checkout, so a checkout that sits
    under the system temp root earns the same verdict as one that does not.
    """

    temp_root = os.path.normcase(os.path.realpath(tempfile.gettempdir()))
    checkout = os.path.normcase(os.path.realpath(str(ROOT))) + os.sep
    meaningful = []
    for entry in entries:
        try:
            raw = os.fspath(entry)
        except TypeError:
            meaningful.append(entry)
            continue
        absolute = os.path.normcase(os.path.realpath(raw))
        if absolute in IMPORT_BOOTSTRAP_ROOTS:
            continue
        try:
            in_scratch = os.path.commonpath((temp_root, absolute)) == temp_root
        except ValueError:
            in_scratch = False
        if (in_scratch and not absolute.startswith(checkout)
                and absolute != temp_root and not os.path.exists(absolute)):
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
    """Run one module and write its counts; reject guarded-seam residue."""

    script_dir = Path(__file__).resolve().parent
    sys.path[:] = [p for p in sys.path if p and Path(p).resolve() != script_dir]
    sys.path.insert(0, import_root)

    before = guarded_state()
    suite = unittest.TestLoader().loadTestsFromName(module)
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=verbosity).run(suite)
    restored = restore_guarded_state(before)
    leaks = leaked_seams(before)
    for seam in leaks:
        sys.stderr.write("leaked whole-interpreter seam: " + seam + "\n")
    payload = {
        "module": module,
        "tests": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors) + len(leaks),
        "skipped": len(result.skipped),
        "expected_failures": len(result.expectedFailures),
        "unexpected": len(result.unexpectedSuccesses),
        "ok": result.wasSuccessful() and not leaks,
        "restored_seams": restored,
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
    """Atomically merge durations so subset runs preserve other timings."""

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

def schedule(modules, times, tests_dir=DEFAULT_TESTS_DIR):
    """Schedule cached runs longest-first and cold repository runs by prior."""

    if not times:
        if Path(tests_dir).resolve() == DEFAULT_TESTS_DIR.resolve():
            rank = {name: index for index, name in enumerate(DEFAULT_COLD_ORDER)}
            return sorted(modules, key=lambda name: (rank.get(name, len(rank)), name))
        return sorted(modules)

    return sorted(modules, key=lambda name: (-times.get(name, float("inf")), name))

def child_env() -> dict:
    """Preserve the environment while pinning only child stdio to UTF-8."""

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    return env

def run_module(module: str, import_root: Path, verbosity: int) -> dict:
    handle, result_path = tempfile.mkstemp(prefix="run_tests_", suffix=".json")
    os.close(handle)
    command = [
        sys.executable, str(Path(__file__).resolve()), "--child", module,
        "--import-root", str(import_root), "--result-file", result_path,
        "--child-verbosity", str(verbosity),
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
    finished = time.monotonic()
    duration = finished - started
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
            "expected_failures": 0,
            "unexpected": 0,
            "ok": False,
            "note": "child wrote no result (exit %d)" % completed.returncode,
        }
    finally:
        try:
            os.unlink(result_path)
        except OSError:
            pass
    if completed.returncode and record.get("ok"):
        record["ok"] = False
        record["note"] = "child exited %d after reporting success" % completed.returncode
    record["duration"] = duration
    record["started"] = started
    record["finished"] = finished
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
    """Preserve failure output; escape only glyphs the host console rejects."""

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

def timing_record(records, wall, requested_jobs, effective_jobs, started) -> dict:
    """Return one revision-stamped, machine-readable suite observation."""

    serial = sum(record["duration"] for record in records)
    outcomes = {
        key: sum(record[key] for record in records)
        for key in ("tests", "failures", "errors", "skipped", "expected_failures", "unexpected")
    }
    active = peak = 0
    events = [(record[edge], 1 if edge == "started" else -1)
              for record in records for edge in ("started", "finished")]
    for _, change in sorted(events, key=lambda event: (event[0], -event[1])):
        active += change
        peak = max(peak, active)
    revision = None
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(ROOT),
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        if completed.returncode == 0:
            revision = completed.stdout.decode("ascii", "replace").strip() or None
    except OSError:
        pass
    return {
        "schema": "orchflows.test-timing.v1",
        "recorded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "revision": revision,
        "platform": {"system": os.name, "description": sys.platform},
        "interpreter": {"version": sys.version.split()[0], "executable": sys.executable},
        "requested_workers": requested_jobs,
        "effective_workers": effective_jobs,
        "wall_time_seconds": round(wall, 6),
        "summed_module_time_seconds": round(serial, 6),
        "occupancy": {
            "capacity_ratio": round(serial / (wall * effective_jobs), 6) if wall else 0.0,
            "peak_active_workers": peak,
        },
        "outcomes": outcomes,
        "ok": all(record["ok"] for record in records),
        "modules": [
            {
                "module": record["module"], "duration_seconds": round(record["duration"], 6),
                "started_seconds": round(record["started"] - started, 6),
                "finished_seconds": round(record["finished"] - started, 6),
                **{key: record[key] for key in
                   ("tests", "failures", "errors", "skipped", "expected_failures", "unexpected", "ok")},
            }
            for record in sorted(records, key=lambda record: record["started"])
        ],
        "limitations": ["CPU and disk utilization are not sampled."],
    }

def save_timing(path: Path, record: dict) -> None:
    """Atomically write optional telemetry without changing suite status."""

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(record, stream, sort_keys=True, indent=1)
        os.replace(tmp, str(path))
    except OSError:
        pass

# --- entry point ------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_tests.py",
        description="Run the unit suite one module per process.",
        epilog="With no MODULE arguments every tests/test_*.py runs.",
    )
    parser.add_argument("modules", metavar="MODULE", nargs="*", help="module name or path to run")
    parser.add_argument(
        "-j", "--jobs", type=int, default=os.cpu_count() or 1,
        help="worker processes (default: CPU count); -j 1 runs modules one at a time in order",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose child test output")
    parser.add_argument("--no-cache", action="store_true",
                        help="ignore the duration cache: use cold-checkout scheduling")
    parser.add_argument(
        "--tests-dir", default=str(DEFAULT_TESTS_DIR), help="directory of test_*.py (default: tests/)"
    )
    parser.add_argument("--shard", metavar="K-of-N", help="run only this shard of the scheduled order")
    parser.add_argument("--scope", help="run only the modules PATH[,PATH] affects (affected_tests.py)")
    parser.add_argument("--timing-file", help="write a machine-readable suite timing record")
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
    run_tests_scope.refuse_positional(args.scope, args.modules)

    tests_dir = Path(args.tests_dir).resolve()
    if not tests_dir.is_dir():
        raise SystemExit("run_tests: no such directory: " + str(tests_dir))
    import_root, prefix, discovered = discover(tests_dir)
    if not discovered:
        raise SystemExit("run_tests: no test_*.py under " + str(tests_dir))
    # Over the sources this run named rather than the whole tree, and ahead of
    # the selection: a scope reaching no module exits 0 in there, which would
    # carry the admission the run still owes away with it.
    admitted = run_tests_scope.admission_paths(
        args.scope, args.modules, tests_dir == DEFAULT_TESTS_DIR.resolve())
    if admitted is not None:
        size_check = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "check_source_sizes.py")] + admitted,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=child_env(),
        )
        if size_check.returncode:
            emit(size_check.stdout.decode("utf-8", "replace"))
            print("FAILED: tracked source-size admission")
            return 1
    if args.scope:
        args.modules = run_tests_scope.select(args.scope, tests_dir, discovered)
    selected = (
        [resolve(name, discovered, prefix) for name in args.modules] if args.modules else discovered
    )

    verbosity = 2 if args.verbose else 1
    # The cache is gitignored, so CI uses the repository's cold-start priors
    # while a local checkout that has run once schedules from measured time.
    # `--no-cache` is how a local run reproduces CI's co-scheduling.
    ordered = run_tests_scope.shard(
        args.shard, schedule(selected, {} if args.no_cache else load_times(), tests_dir))
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
    status = report(records, wall, jobs)
    timing_path = Path(args.timing_file) if args.timing_file else (
        TIMING_PATH if tests_dir == DEFAULT_TESTS_DIR.resolve() and not args.modules else None
    )
    if timing_path is not None:
        save_timing(timing_path, timing_record(records, wall, args.jobs, jobs, started))
    return status

if __name__ == "__main__":
    # Guarded for Windows: any spawn-based re-import of this module must
    # not re-enter main().
    raise SystemExit(main(sys.argv[1:]))
