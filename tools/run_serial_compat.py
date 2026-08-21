#!/usr/bin/env python3
"""Run the selected or exhaustive suite in one interpreter.

The selected lane is experimental: it proves exact discovery identity and
executes the committed state sentinels without replacing exhaustive serial.
Stdlib only, Python 3.9+, POSIX and Windows.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import unittest
from collections import OrderedDict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = ROOT / "tests"
MANIFEST_PATH = TESTS_DIR / "serial_compat_manifest.json"
RECORD_PATH = ROOT / ".orch" / "serial-compat.json"


def load_manifest(path: Path = MANIFEST_PATH) -> dict:
    """Load the committed identity, sentinel, and mutation-owner contract."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema") != "orchflows.serial-compat.v1":
        raise ValueError("unsupported serial compatibility manifest")
    return data


def flatten(suite):
    """Yield cases from a unittest suite without executing its fixtures."""

    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def discover_cases(tests_dir: Path = TESTS_DIR):
    """Discover the same identities as ``unittest discover -s tests``."""

    tests_dir = Path(tests_dir).resolve()
    for path in tests_dir.glob("test*.py"):
        cached = sys.modules.get(path.stem)
        cached_file = getattr(cached, "__file__", None)
        if cached_file is not None and Path(cached_file).resolve().parent != tests_dir:
            del sys.modules[path.stem]
    before = list(sys.path)
    try:
        suite = unittest.TestLoader().discover(str(tests_dir))
        return list(flatten(suite))
    finally:
        sys.path[:] = before


def revision(root: Path = ROOT):
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return None
    if completed.returncode:
        return None
    return completed.stdout.decode("ascii", "replace").strip() or None


def _summary(results):
    return {
        "tests": sum(result.testsRun for result in results),
        "failures": sum(len(result.failures) for result in results),
        "errors": sum(len(result.errors) for result in results),
        "skipped": sum(len(result.skipped) for result in results),
        "expected_failures": sum(len(result.expectedFailures) for result in results),
        "unexpected_successes": sum(len(result.unexpectedSuccesses) for result in results),
    }


def run_selected(tests_dir: Path, manifest: dict, stream=None, verbosity: int = 1) -> dict:
    """Discover all cases, then run only committed sentinels in this process."""

    started = time.monotonic()
    cases = discover_cases(tests_dir)
    by_id = {}
    for case in cases:
        by_id.setdefault(case.id(), []).append(case)
    entries = manifest.get("sentinels", [])
    missing = [entry["id"] for entry in entries if len(by_id.get(entry["id"], ())) != 1]
    if missing:
        raise ValueError("selected identity missing or duplicated: " + ", ".join(missing))

    groups = OrderedDict()
    for entry in entries:
        groups.setdefault(entry["module"], []).append(by_id[entry["id"]][0])
    output = stream if stream is not None else sys.stderr
    results = []
    for module, selected in groups.items():
        output.write("selected module: %s (%d sentinels)\n" % (module, len(selected)))
        result = unittest.TextTestRunner(stream=output, verbosity=verbosity).run(
            unittest.TestSuite(selected)
        )
        results.append(result)
    outcomes = _summary(results)
    ok = bool(entries) and all(result.wasSuccessful() for result in results)
    return {
        "schema": "orchflows.serial-compat-observation.v1",
        "mode": "selected",
        "revision": revision(),
        "recorded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "interpreter": {
            "pid": os.getpid(),
            "version": sys.version.split()[0],
            "executable": sys.executable,
        },
        "discovery": {"count": len(cases)},
        "sentinels": {"count": len(entries)},
        "outcomes": outcomes,
        "wall_time_seconds": round(time.monotonic() - started, 6),
        "ok": ok,
    }


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(MANIFEST_PATH))
    parser.add_argument("--tests-dir", default=str(TESTS_DIR))
    parser.add_argument("--record", default=str(RECORD_PATH))
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    record = run_selected(
        Path(args.tests_dir),
        load_manifest(Path(args.manifest)),
        verbosity=2 if args.verbose else 1,
    )
    path = Path(args.record)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, sort_keys=True, indent=1), encoding="utf-8")
    print(json.dumps(record, sort_keys=True))
    return 0 if record["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
