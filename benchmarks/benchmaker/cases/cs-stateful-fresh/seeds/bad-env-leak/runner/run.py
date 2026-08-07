#!/usr/bin/env python3
"""schema-migration benchmark runner. Executable interface of this package.

    python run.py IMPL

IMPL is a directory holding the tool file named by the runnable case
set, or a direct path to it. Emits one JSON result object on stdout;
exit 0 when the aggregate verdict is pass, 1 when it is fail, 2 on
usage errors. Python 3.9 stdlib only. Every case's state directory is
constructed in scratch space; the two-run transcript executes the
implementation twice against the SAME state directory with a pinned
environment; nothing inside the package tree is written.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

ENV_ALLOWLIST = ("SYSTEMROOT", "SystemRoot", "WINDIR", "TEMP", "TMP", "COMSPEC")


def pinned_env():
    """Harness environment: allowlist plus the migration guard export."""
    env = {"PYTHONDONTWRITEBYTECODE": "1", "MIGRATION_SAFE": "1"}
    for key in ENV_ALLOWLIST:
        if key in os.environ:
            env[key] = os.environ[key]
    return env


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
    with open(os.path.join(root, locator.replace("/", os.sep)), "r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_impl(raw, tool):
    path = os.path.abspath(raw)
    if os.path.isdir(path):
        path = os.path.join(path, tool)
    if not os.path.isfile(path):
        raise SystemExit("run.py: no such implementation: %s" % raw)
    return path


def serialize(value):
    return (json.dumps(value, sort_keys=True) + "\n").encode("utf-8")


def expected_state(case):
    migrated = serialize(
        {"schema": 2, "records": [{"name": name, "qty": qty} for name, qty in case["records"]]}
    )
    checksum = "sha256:" + hashlib.sha256(migrated).hexdigest()
    journal = serialize({"applied": ["v1-to-v2"], "checksum": checksum})
    return migrated, journal


def read_file(path):
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as handle:
        return handle.read()


def execute(impl, state_dir):
    done = subprocess.run(
        [sys.executable, impl, state_dir],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=pinned_env(),
        timeout=30,
    )
    return done.returncode


def assert_state(state_dir, migrated, journal, phase):
    problems = []
    data = read_file(os.path.join(state_dir, "data.json"))
    log = read_file(os.path.join(state_dir, "journal.json"))
    if data != migrated:
        problems.append("%s: data.json does not match the migrated bytes" % phase)
    if log != journal:
        problems.append("%s: journal.json does not match the complete journal bytes" % phase)
    return problems


def run_case(case, impl, scratch_root):
    migrated, journal = expected_state(case)
    state_dir = tempfile.mkdtemp(prefix=case["id"] + "-", dir=scratch_root)
    if case["pre_migrated"]:
        with open(os.path.join(state_dir, "data.json"), "wb") as handle:
            handle.write(migrated)
        with open(os.path.join(state_dir, "journal.json"), "wb") as handle:
            handle.write(journal)
    else:
        with open(os.path.join(state_dir, "data.json"), "wb") as handle:
            handle.write(serialize({"schema": 1, "records": case["records"]}))
    problems = []
    runs = []

    code = execute(impl, state_dir)
    first_ok = code == 0
    if code != 0:
        problems.append("run 1: exit %d, want 0" % code)
    first_problems = assert_state(state_dir, migrated, journal, "after run 1")
    problems.extend(first_problems)
    runs.append({"run": 1, "state_dir": state_dir, "ok": first_ok and not first_problems})

    code = execute(impl, state_dir)
    second_ok = code == 0
    if code != 0:
        problems.append("run 2: exit %d, want 0" % code)
    second_problems = assert_state(state_dir, migrated, journal, "after run 2 (escaped state)")
    problems.extend(second_problems)
    runs.append({"run": 2, "state_dir": state_dir, "ok": second_ok and not second_problems})

    return {
        "id": case["id"],
        "pass": not problems,
        "detail": "; ".join(problems) or "ok",
        "runs": runs,
    }


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
    scratch_root = tempfile.mkdtemp(prefix="migrate-bench-")
    try:
        results = [run_case(case, impl, scratch_root) for case in case_set["cases"]]
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)
    required = set(scoring["required_case_ids"])
    overall = all(r["pass"] for r in results if r["id"] in required)
    report = {"impl": impl, "cases": results, "pass": overall}
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
