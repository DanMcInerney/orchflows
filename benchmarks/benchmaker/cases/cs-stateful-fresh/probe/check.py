#!/usr/bin/env python3
"""Probe for cs-stateful-fresh. NOT the benchmark under test.

Usage (from the case directory):

    uv run --no-project python probe/check.py IMPL

IMPL is a package directory (``target`` or ``seeds/<slug>``); it may
also arrive absolute in ``CASE_IMPL``. Paths resolve against the
caller's directory and then against the case directory.

Checks (exit 0 all pass; exit 1 with one line per violation):

- P0.a manifest present, ten fields, benchmark_identity recomputes.
- P0.b every component digest verifies over the shipped bytes at its
       locator, resolved relative to the package root.
- P0.c qualification entries verdict-contract complete; no overall
       PASS with a required FAIL; no PASS entry with empty evidence;
       gaps explicit.
- P0.d inner discrimination: the package's own runner+scoring passes
       the inner reference and good variants and fails every inner
       bad variant including the inner near-miss.
- st.1 two-run transcript: for every case, the runner's transcript
       records at least two executions of the inner target against
       the SAME state directory — the escaped state is reached
       through the implementation's own first run, never by harness
       construction.
- st.2 environment pinning: with a poison variable set in the
       probe's environment, the package must still fail the inner
       impl whose defect hides behind that variable — a pinned
       scoring path is immune to ambient environment.

Hygiene: the implementation under test and the inner pool are copied
to a scratch directory before any execution; nothing under the case
directory is ever written.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

CASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_FIELDS = [
    "benchmark_identity",
    "evaluation_design",
    "runnable_cases",
    "runner",
    "scoring",
    "provenance",
    "qualification",
    "expected_cost",
    "gaps",
    "protected_evidence",
]
COMPONENTS = MANIFEST_FIELDS[1:7]
POISON = ("MIGRATION_SAFE", "1")
ENV_SENSITIVE_BAD = "bad-remigrate"
RUN_TIMEOUT = 90


def resolve_impl():
    raw = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CASE_IMPL")
    if not raw:
        raw = "target"
    for candidate in (raw, os.path.join(CASE_DIR, raw)):
        if os.path.isdir(candidate):
            return os.path.abspath(candidate)
    return None


def sha256_file(path):
    with open(path, "rb") as handle:
        return "sha256:" + hashlib.sha256(handle.read()).hexdigest()


def canonical_identity(manifest):
    payload = {k: v for k, v in manifest.items() if k != "benchmark_identity"}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def run_runner(runner, impl, cwd, poison=False):
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if poison:
        env[POISON[0]] = POISON[1]
    else:
        env.pop(POISON[0], None)
    done = subprocess.run(
        [sys.executable, runner, impl],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=env,
        timeout=RUN_TIMEOUT,
    )
    try:
        report = json.loads(done.stdout.decode("utf-8"))
    except ValueError:
        report = None
    return done.returncode, report


def main():
    impl_dir = resolve_impl()
    if impl_dir is None:
        sys.stderr.write("probe: no such implementation directory\n")
        return 2

    failures = []

    def fail(check, message):
        failures.append("%s: %s" % (check, message))

    scratch = tempfile.mkdtemp(prefix="cs-stateful-fresh-")
    try:
        pkg = os.path.join(scratch, "pkg")
        pool = os.path.join(scratch, "pool")
        shutil.copytree(impl_dir, pkg)
        shutil.copytree(os.path.join(CASE_DIR, "evidence", "inner-impls"), pool)

        # ---- P0.a ----------------------------------------------------
        manifest = None
        manifest_path = os.path.join(pkg, "manifest.json")
        if not os.path.isfile(manifest_path):
            fail("P0.a", "no manifest.json at the package root")
        else:
            try:
                with open(manifest_path, "r", encoding="utf-8") as handle:
                    manifest = json.load(handle)
            except ValueError as error:
                fail("P0.a", "manifest.json is not valid JSON: %s" % error)
        if manifest is not None:
            for field in MANIFEST_FIELDS:
                if field not in manifest:
                    fail("P0.a", "manifest is missing field '%s'" % field)
            if all(field in manifest for field in MANIFEST_FIELDS):
                recomputed = canonical_identity(manifest)
                if recomputed != manifest["benchmark_identity"]:
                    fail(
                        "P0.a",
                        "benchmark_identity does not recompute: recorded %s, canonical %s"
                        % (manifest["benchmark_identity"], recomputed),
                    )

        # ---- P0.b ----------------------------------------------------
        located = {}
        if manifest is not None:
            for name in COMPONENTS:
                ref = manifest.get(name)
                if not isinstance(ref, dict) or "identity" not in ref or "locator" not in ref:
                    fail("P0.b", "component '%s' lacks identity/locator" % name)
                    continue
                path = os.path.join(pkg, ref["locator"].replace("/", os.sep))
                if not os.path.isfile(path):
                    fail("P0.b", "component '%s' locator '%s' resolves to nothing" % (name, ref["locator"]))
                    continue
                actual = sha256_file(path)
                if actual != ref["identity"]:
                    fail("P0.b", "component '%s' digest mismatch: recorded %s, shipped %s" % (name, ref["identity"], actual))
                    continue
                located[name] = path

        # ---- P0.c ----------------------------------------------------
        if "qualification" in located:
            with open(located["qualification"], "r", encoding="utf-8") as handle:
                qualification = json.load(handle)
            entries = qualification.get("entries")
            if not isinstance(entries, list) or not entries:
                fail("P0.c", "qualification carries no entries")
                entries = []
            required_fail = False
            for entry in entries:
                label = entry.get("criterion", "<unnamed>")
                for key in ("verdict", "oracle", "oracle_class", "evidence", "covers", "required"):
                    if key not in entry:
                        fail("P0.c", "entry '%s' lacks '%s'" % (label, key))
                verdict = entry.get("verdict")
                if verdict == "FAIL" and entry.get("required") is True:
                    required_fail = True
                evidence = entry.get("evidence")
                empty = evidence in (None, "", [], {}) or (
                    isinstance(evidence, dict) and not any(str(v).strip() for v in evidence.values())
                )
                if verdict == "PASS" and empty:
                    fail("P0.c", "entry '%s' is PASS with empty evidence" % label)
            overall = (qualification.get("overall") or {}).get("verdict")
            if overall == "PASS" and required_fail:
                fail("P0.c", "overall PASS coexists with a required FAIL")
            if "gaps" not in qualification:
                fail("P0.c", "qualification has no explicit gaps field")

        # ---- P0.d ----------------------------------------------------
        reference_report = None
        pool_impls = sorted(
            entry for entry in os.listdir(pool) if os.path.isdir(os.path.join(pool, entry))
        )
        if "runner" in located:
            for name in pool_impls:
                expect_pass = not name.startswith("bad")
                code, report = run_runner(located["runner"], os.path.join(pool, name), pkg)
                if report is None:
                    fail("P0.d", "runner emitted no JSON verdict for inner impl '%s' (exit %s)" % (name, code))
                    continue
                if name == "reference":
                    reference_report = report
                got_pass = bool(report.get("pass")) and code == 0
                if expect_pass and not got_pass:
                    failing = [c["id"] for c in report.get("cases", []) if not c.get("pass")]
                    fail("P0.d", "inner impl '%s' must pass but failed cases %s" % (name, failing))
                if not expect_pass and got_pass:
                    fail("P0.d", "inner bad impl '%s' passed the package's runner+scoring" % name)

        # ---- st.1 two-run transcript, same state directory --------------
        if reference_report is not None:
            for case in reference_report.get("cases", []):
                runs = case.get("runs")
                if not isinstance(runs, list) or len(runs) < 2:
                    fail(
                        "st.1",
                        "case '%s' transcript records %s run(s); the escaped second-run state is unreachable"
                        % (case.get("id", "?"), len(runs) if isinstance(runs, list) else "no"),
                    )
                    continue
                dirs = {str(run.get("state_dir")) for run in runs}
                if len(dirs) != 1:
                    fail(
                        "st.1",
                        "case '%s' run 2 executed against a different state directory than run 1 "
                        "(escaped state reached by harness construction, not by the implementation's own first run)"
                        % case.get("id", "?"),
                    )
        elif "runner" in located:
            fail("st.1", "no reference transcript available to audit")

        # ---- st.2 environment pinning -----------------------------------
        if "runner" in located and ENV_SENSITIVE_BAD in pool_impls:
            code, report = run_runner(
                located["runner"], os.path.join(pool, ENV_SENSITIVE_BAD), pkg, poison=True
            )
            if report is None:
                fail("st.2", "runner emitted no JSON verdict under the poison environment (exit %s)" % code)
            elif bool(report.get("pass")) and code == 0:
                fail(
                    "st.2",
                    "with %s=%s ambient, inner bad impl '%s' passed: the scoring path does not pin "
                    "the inner process environment" % (POISON[0], POISON[1], ENV_SENSITIVE_BAD),
                )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    if failures:
        sys.stderr.write("probe FAIL (%s): %d violation(s)\n" % (impl_dir, len(failures)))
        for line in failures:
            sys.stderr.write("  - %s\n" % line)
        return 1
    sys.stdout.write("probe PASS (%s): 6 checks (P0.a-P0.d, st.1-st.2)\n" % impl_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
