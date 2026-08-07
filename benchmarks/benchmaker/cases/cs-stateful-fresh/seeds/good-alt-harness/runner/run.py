#!/usr/bin/env python3
"""schema-migration benchmark runner — alternate harness, same laws.

Same executable interface and result schema as the reference runner
(`python run.py IMPL`; JSON on stdout with per-case ``runs``
transcripts; exit 0/1/2), same two-run law against one state
directory, same pinned environment. The transcript format differs:
phase-labelled run records with explicit check ledgers, produced by a
phase table instead of straight-line code.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

KEEP = ("SYSTEMROOT", "SystemRoot", "WINDIR", "TEMP", "TMP", "COMSPEC")
PHASES = ("initial-migration", "escaped-state-replay")


def controlled_environment():
    kept = {name: os.environ[name] for name in KEEP if name in os.environ}
    kept["PYTHONDONTWRITEBYTECODE"] = "1"
    return kept


def find_root():
    here = os.path.abspath(os.path.dirname(__file__))
    while not os.path.isfile(os.path.join(here, "manifest.json")):
        up = os.path.dirname(here)
        if up == here:
            raise SystemExit("run.py: manifest.json not found")
        here = up
    return here


def component(root, manifest, name):
    path = os.path.join(root, manifest[name]["locator"].replace("/", os.sep))
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def canonical(value):
    return (json.dumps(value, sort_keys=True) + "\n").encode("utf-8")


def goal_state(case):
    data = canonical({"schema": 2, "records": [{"name": n, "qty": q} for n, q in case["records"]]})
    journal = canonical(
        {"applied": ["v1-to-v2"], "checksum": "sha256:" + hashlib.sha256(data).hexdigest()}
    )
    return data, journal


def write_bytes(path, blob):
    with open(path, "wb") as handle:
        handle.write(blob)


def snapshot(state_dir):
    out = {}
    for name in ("data.json", "journal.json"):
        path = os.path.join(state_dir, name)
        if os.path.isfile(path):
            with open(path, "rb") as handle:
                out[name] = handle.read()
        else:
            out[name] = None
    return out


def audit(state_dir, data, journal):
    seen = snapshot(state_dir)
    return [
        ("data-bytes-lawful", seen["data.json"] == data),
        ("journal-bytes-complete", seen["journal.json"] == journal),
    ]


def drive_case(case, impl, workspace):
    data, journal = goal_state(case)
    state_dir = tempfile.mkdtemp(prefix="state-" + case["id"] + "-", dir=workspace)
    if case["pre_migrated"]:
        write_bytes(os.path.join(state_dir, "data.json"), data)
        write_bytes(os.path.join(state_dir, "journal.json"), journal)
    else:
        write_bytes(
            os.path.join(state_dir, "data.json"),
            canonical({"schema": 1, "records": case["records"]}),
        )
    faults = []
    transcript = []
    for number, phase in enumerate(PHASES, start=1):
        proc = subprocess.run(
            [sys.executable, impl, state_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=controlled_environment(),
            timeout=30,
        )
        ledger = audit(state_dir, data, journal)
        clean = proc.returncode == 0 and all(ok for _, ok in ledger)
        if proc.returncode != 0:
            faults.append("%s: exit %d, want 0" % (phase, proc.returncode))
        faults.extend("%s: %s violated" % (phase, name) for name, ok in ledger if not ok)
        transcript.append(
            {
                "run": number,
                "phase": phase,
                "state_dir": state_dir,
                "checks": [name for name, _ in ledger],
                "ok": clean,
            }
        )
    return {
        "id": case["id"],
        "pass": not faults,
        "detail": "; ".join(faults) or "ok",
        "runs": transcript,
    }


def main():
    if len(sys.argv) != 2:
        sys.stderr.write("usage: run.py IMPL\n")
        return 2
    root = find_root()
    with open(os.path.join(root, "manifest.json"), "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    suite = component(root, manifest, "runnable_cases")
    scoring = component(root, manifest, "scoring")
    impl = os.path.abspath(sys.argv[1])
    if os.path.isdir(impl):
        impl = os.path.join(impl, suite["tool"])
    if not os.path.isfile(impl):
        sys.stderr.write("run.py: no such implementation: %s\n" % sys.argv[1])
        return 2
    workspace = tempfile.mkdtemp(prefix="migrate-bench-alt-")
    try:
        outcomes = [drive_case(case, impl, workspace) for case in suite["cases"]]
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
    must = set(scoring["required_case_ids"])
    verdict = all(item["pass"] for item in outcomes if item["id"] in must)
    report = {"impl": impl, "cases": outcomes, "pass": verdict}
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0 if verdict else 1


if __name__ == "__main__":
    sys.exit(main())
