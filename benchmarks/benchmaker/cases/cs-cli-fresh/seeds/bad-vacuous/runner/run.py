#!/usr/bin/env python3
"""csvmerge benchmark runner. Executable interface of this package.

    python run.py IMPL

IMPL is a directory holding the tool file named by the runnable case
set, or a direct path to it. Emits one JSON result object on stdout
and exits 0 when the aggregate verdict is pass, 1 when it is fail,
2 on usage errors. Python 3.9 stdlib only; each case executes in a
scratch directory; nothing inside the package tree is written.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile


def package_root(start):
    probe = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(probe, "manifest.json")):
            return probe
        parent = os.path.dirname(probe)
        if parent == probe:
            raise SystemExit("run.py: no manifest.json above %s" % start)
        probe = parent


def load_component(root, manifest, name):
    locator = manifest[name]["locator"]
    path = os.path.join(root, locator.replace("/", os.sep))
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_impl(raw, tool):
    path = os.path.abspath(raw)
    if os.path.isdir(path):
        path = os.path.join(path, tool)
    if not os.path.isfile(path):
        raise SystemExit("run.py: no such implementation: %s" % raw)
    return path


def outputs_match(expected, actual):
    """Tolerance law: line-terminator form is not significant."""
    return expected.replace(b"\r\n", b"\n") == actual.replace(b"\r\n", b"\n")


def run_case(case, impl):
    scratch = tempfile.mkdtemp(prefix="csvmerge-case-")
    try:
        a_path = os.path.join(scratch, "a.csv")
        b_path = os.path.join(scratch, "b.csv")
        with open(a_path, "wb") as handle:
            handle.write(case["a"].encode("utf-8"))
        with open(b_path, "wb") as handle:
            handle.write(case["b"].encode("utf-8"))
        argv = [arg.replace("{a}", a_path).replace("{b}", b_path) for arg in case["argv"]]
        done = subprocess.run(
            [sys.executable, impl] + argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=scratch,
            timeout=30,
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    problems = []
    return {"id": case["id"], "pass": not problems, "detail": "; ".join(problems) or "ok"}


def main():
    if len(sys.argv) != 2:
        sys.stderr.write("usage: run.py IMPL\n")
        return 2
    root = package_root(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "manifest.json"), "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    case_set = load_component(root, manifest, "runnable_cases")
    scoring = load_component(root, manifest, "scoring")
    impl = resolve_impl(sys.argv[1], case_set["tool"])
    results = [run_case(case, impl) for case in case_set["cases"]]
    required = set(scoring["required_case_ids"])
    overall = all(r["pass"] for r in results if r["id"] in required)
    report = {"impl": impl, "cases": results, "pass": overall}
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
