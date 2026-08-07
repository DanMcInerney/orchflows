#!/usr/bin/env python3
"""chooseplan benchmark runner.

Usage: python run.py <impl_dir>

<impl_dir> holds planner.py exposing choose_plan(query) -> str. The
runner locates its package root by walking up to manifest.json, loads
the case set and scoring policy through the manifest locators, runs
every case, prints one JSON result line, and exits 0 iff no required
case mismatches. Python 3.9 stdlib only; no network; no writes.
"""
import importlib.util
import json
import os
import sys
from pathlib import Path


def find_root(start):
    here = Path(start).resolve()
    for candidate in [here] + list(here.parents):
        if (candidate / "manifest.json").is_file():
            return candidate
    raise SystemExit("run.py: no manifest.json at or above " + str(here))


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    if len(sys.argv) != 2:
        print("usage: run.py <impl_dir>")
        return 2
    root = find_root(Path(__file__).parent)
    manifest = load_json(root / "manifest.json")
    cases = load_json(root / manifest["runnable_cases"]["locator"])["cases"]
    policy = load_json(root / manifest["scoring"]["locator"])
    required = set(policy.get("required", []))

    records = list(cases)
    protected_ids = []
    # -- protected workload extension --
    protected_root = os.environ.get("BENCH_PROTECTED_DIR")
    if protected_root:
        workload = Path(protected_root) / "cs-antigoodhart-2" / "workload.json"
        if workload.is_file():
            held = load_json(workload)
            for record in held.get("cases", []):
                records.append(record)
                protected_ids.append(record["id"])
                if policy.get("protected_required", True):
                    required.add(record["id"])
    # -- end protected workload extension --

    impl = Path(sys.argv[1]).resolve()
    spec = importlib.util.spec_from_file_location(
        "planner_under_test", impl / "planner.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    failed = []
    for record in records:
        got = module.choose_plan(dict(record["query"]))
        if got != record["expected_plan"]:
            failed.append(record["id"])

    required_failed = sorted(set(failed) & required)
    print(
        json.dumps(
            {
                "impl": impl.name,
                "cases_run": len(records),
                "failed": sorted(failed),
                "protected_ids": protected_ids,
                "required_failed": required_failed,
            },
            sort_keys=True,
        )
    )
    return 1 if required_failed else 0


if __name__ == "__main__":
    sys.exit(main())
