"""Scoring entry point and aggregation law for the token-bucket benchmark.

Usage: python score.py IMPL_DIR

IMPL_DIR holds ``tokenbucket.py``. Aggregation: every case marked required
must pass; any required failure fails the run. Exit 0 pass, 1 fail, 2 usage.
"""
import importlib.util
import json
import sys
from pathlib import Path


def package_root(start):
    here = Path(start).resolve()
    for candidate in (here,) + tuple(here.parents):
        if (candidate / "manifest.json").is_file():
            return candidate
    raise SystemExit("score.py: no manifest.json at or above %s" % start)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    if len(sys.argv) != 2:
        sys.stderr.write("usage: score.py IMPL_DIR\n")
        return 2
    impl_dir = Path(sys.argv[1])
    if not impl_dir.is_dir():
        sys.stderr.write("score.py: no such implementation directory: %s\n" % impl_dir)
        return 2
    root = package_root(Path(__file__).parent)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    runner = load_module("benchmark_runner", root / manifest["runner"]["locator"])
    cases_path = root / manifest["runnable_cases"]["locator"]
    failures = runner.run_all(cases_path, impl_dir)
    required_failures = [f for f in failures if f[1]]
    for case_id, required, detail in failures:
        sys.stderr.write(
            "FAIL %s (%s): %s\n" % (case_id, "required" if required else "secondary", detail)
        )
    if required_failures:
        sys.stderr.write("score: FAIL — %d required case(s) failed\n" % len(required_failures))
        return 1
    sys.stdout.write("score: PASS — all required cases passed\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
