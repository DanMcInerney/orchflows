#!/usr/bin/env python3
"""Probe for cs-cli-fresh. NOT the benchmark under test.

Usage (from the case directory):

    uv run --no-project python probe/check.py IMPL

IMPL is a package directory (``target`` or ``seeds/<slug>``); it may
also arrive absolute in ``CASE_IMPL``. Paths resolve against the
caller's directory and then against the case directory, so the probe
runs from the case directory or the repository root.

Checks (exit 0 all pass; exit 1 with one line per violation):

- P0.a  manifest present, nine fields.
- P0.b  every component locator resolves to shipped bytes, relative to
        the package root.
- P0.c  qualification entries verdict-contract complete; no overall
        PASS with a required FAIL; no PASS entry with empty evidence;
        gaps explicit.
- P0.d  inner discrimination: the package's own runner+scoring passes
        the inner reference and good variants and fails every inner
        bad variant including the inner near-miss.
- cli.1 tolerance breadth: the package oracle accepts CRLF-terminated
        otherwise-valid output.
- cli.2 at least one package oracle is anchored to an exhibited
        transcript, or an impossibility reason (not an implementation
        artifact) is recorded.
- cli.3 qualification independence: no required verdict's evidence
        cites only the builder context recorded in provenance (the
        check that separates the self-reported-score-trusted seed).

Hygiene: the implementation under test and the inner pool are copied
to a scratch directory before any execution; nothing under the case
directory is ever written.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

CASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_FIELDS = [
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
COMPONENTS = MANIFEST_FIELDS[0:6]
RUN_TIMEOUT = 45


# ---- P0.e: the post-qualification manifest fields -------------------
# `example-workflows/references/benchmaker-manifest.md` owns the eight. None is
# re-derivable after the fact, so a package that omits one cannot be repaired
# by a consumer. This case covers `resolution`:
# a byte-exact oracle has a rerun spread of zero, so the smallest reportable
# difference rests on the one-case floor and the max() is checkable.
# The other fields are legal here and covered by the cases whose angle reaches
# them; `tools/validate_cases.py` reads PROBED_MANIFEST_FIELDS and refuses a
# case set that leaves one of the eight uncovered and unrecorded.
POST_QUALIFICATION_FIELDS = frozenset(
    (
        "anchors",
        "builders",
        "reference_audit",
        "attack_audit",
        "measurement",
        "resolution",
        "retirement_trigger",
        "incomparability",
    )
)
PROBED_MANIFEST_FIELDS = {"resolution": "constrained"}
REQUIRED_MANIFEST_FIELDS = frozenset(MANIFEST_FIELDS)
ALLOWED_MANIFEST_FIELDS = REQUIRED_MANIFEST_FIELDS | POST_QUALIFICATION_FIELDS

def _leading_number(text):
    digits = ""
    for char in text:
        if char.isdigit() or (char == "." and digits):
            digits += char
        elif digits:
            break
    digits = digits.rstrip(".")
    return float(digits) if digits else None


def _resolution_failures(manifest, out):
    record = manifest.get("resolution")
    if not isinstance(record, dict):
        out.append("'resolution' must state the smallest reportable difference, "
                   "max(measured rerun spread, one case)")
        return
    one_case = record.get("one_case")
    if isinstance(one_case, bool) or not isinstance(one_case, int) or one_case < 1:
        out.append("resolution states no one-case floor")
    spread = record.get("measured_rerun_spread")
    if spread is None:
        if not str(record.get("note") or "").strip():
            out.append("resolution leaves the rerun spread unmeasured with no note")
    elif isinstance(spread, bool) or not isinstance(spread, (int, float)) or spread < 0:
        out.append("resolution 'measured_rerun_spread' must be a measured number or null")
    declared = record.get("smallest_reportable_difference")
    if not (isinstance(declared, str) and declared.strip()):
        out.append("resolution states no smallest reportable difference")
        return
    reported = _leading_number(declared)
    floor = max(
        one_case if isinstance(one_case, int) and not isinstance(one_case, bool) else 1,
        spread if isinstance(spread, (int, float)) and not isinstance(spread, bool) else 0,
    )
    if reported is None:
        out.append("resolution's smallest reportable difference names no number of cases")
    elif reported != floor:
        out.append("resolution reports %g where max(rerun spread, one case) is %g"
                   % (reported, floor))


def post_qualification_failures(manifest):
    """P0.e — the field(s) this case covers, against the manifest contract."""
    if not isinstance(manifest, dict):
        return ["manifest is not a JSON object"]
    out = []
    _resolution_failures(manifest, out)
    return out


def resolve_impl():
    raw = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CASE_IMPL")
    if not raw:
        raw = "target"
    for candidate in (raw, os.path.join(CASE_DIR, raw)):
        if os.path.isdir(candidate):
            return os.path.abspath(candidate)
    return None


def run_runner(runner, impl, cwd):
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        done = subprocess.run(
            [sys.executable, runner, impl],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=env,
            timeout=RUN_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return "timeout after %ss" % RUN_TIMEOUT, None
    try:
        report = json.loads(done.stdout.decode("utf-8"))
    except ValueError:
        report = None
    if not isinstance(report, dict):
        report = None
    return done.returncode, report


def failing_ids(report):
    cases = report.get("cases")
    if not isinstance(cases, list):
        return []
    return [c.get("id") for c in cases if isinstance(c, dict) and not c.get("pass")]


def load_transcripts():
    path = os.path.join(CASE_DIR, "evidence", "transcripts.md")
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    transcripts = {}
    for block in re.findall(r"```json\n(.*?)```", text, re.S):
        record = json.loads(block)
        transcripts[record["id"]] = record
    return transcripts


def anchored_case_matches(case, transcript):
    raw_argv = case.get("argv")
    if not isinstance(raw_argv, list) or not all(isinstance(arg, str) for arg in raw_argv):
        return False
    argv = [arg.replace("{a}", "a.csv").replace("{b}", "b.csv") for arg in raw_argv]
    return (
        argv == transcript["argv"]
        and case.get("a") == transcript["files"]["a.csv"]
        and case.get("b") == transcript["files"]["b.csv"]
        and case.get("stdout") == transcript["stdout"]
        and case.get("exit") == transcript["exit"]
    )


def main():
    impl_dir = resolve_impl()
    if impl_dir is None:
        sys.stderr.write("probe: no such implementation directory\n")
        return 2

    failures = []

    def fail(check, message):
        failures.append("%s: %s" % (check, message))

    scratch = tempfile.mkdtemp(prefix="cs-cli-fresh-")
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
        if manifest is not None and not isinstance(manifest, dict):
            fail("P0.a", "manifest.json is not a JSON object")
            manifest = None
        if manifest is not None:
            for field in MANIFEST_FIELDS:
                if field not in manifest:
                    fail("P0.a", "manifest is missing field '%s'" % field)
            for message in post_qualification_failures(manifest):
                fail("P0.e", message)

        # ---- P0.b ----------------------------------------------------
        located = {}
        if manifest is not None:
            for name in COMPONENTS:
                ref = manifest.get(name)
                if not isinstance(ref, dict) or "locator" not in ref:
                    fail("P0.b", "component '%s' is not a locator reference" % name)
                    continue
                path = os.path.join(pkg, ref["locator"].replace("/", os.sep))
                if not os.path.isfile(path):
                    fail("P0.b", "component '%s' locator '%s' resolves to nothing" % (name, ref["locator"]))
                    continue
                located[name] = path

        # ---- P0.c ----------------------------------------------------
        qualification = None
        if "qualification" in located:
            with open(located["qualification"], "r", encoding="utf-8") as handle:
                try:
                    qualification = json.load(handle)
                except ValueError as error:
                    fail("P0.c", "qualification component is not valid JSON: %s" % error)
            if qualification is not None and not isinstance(qualification, dict):
                fail("P0.c", "qualification component is not a JSON object")
                qualification = None
        if qualification is not None:
            entries = qualification.get("entries")
            if not isinstance(entries, list) or not entries:
                fail("P0.c", "qualification carries no entries")
                entries = []
            required_fail = False
            for entry in entries:
                if not isinstance(entry, dict):
                    fail("P0.c", "qualification entry is not a JSON object")
                    continue
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
            overall = qualification.get("overall") or {}
            if not isinstance(overall, dict):
                fail("P0.c", "qualification overall must be an object carrying a verdict")
            elif overall.get("verdict") == "PASS" and required_fail:
                fail("P0.c", "overall PASS coexists with a required FAIL")
            if "gaps" not in qualification:
                fail("P0.c", "qualification has no explicit gaps field")

        # ---- P0.d ----------------------------------------------------
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
                got_pass = bool(report.get("pass")) and code == 0
                if expect_pass and not got_pass:
                    fail("P0.d", "inner impl '%s' must pass but failed cases %s" % (name, failing_ids(report)))
                if not expect_pass and got_pass:
                    fail("P0.d", "inner bad impl '%s' passed the package's runner+scoring" % name)

        # ---- cli.1 tolerance breadth ----------------------------------
        if "runner" in located:
            wrapper_dir = os.path.join(scratch, "crlf-wrapper")
            os.makedirs(wrapper_dir)
            reference_tool = os.path.join(pool, "reference", "csvmerge.py")
            wrapper = (
                "import subprocess, sys\n"
                "REF = %r\n"
                "proc = subprocess.run([sys.executable, REF] + sys.argv[1:],\n"
                "                      stdout=subprocess.PIPE)\n"
                "sys.stdout.buffer.write(proc.stdout.replace(b'\\n', b'\\r\\n'))\n"
                "sys.exit(proc.returncode)\n"
            ) % reference_tool
            with open(os.path.join(wrapper_dir, "csvmerge.py"), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(wrapper)
            code, report = run_runner(located["runner"], wrapper_dir, pkg)
            if report is None or not (bool(report.get("pass")) and code == 0):
                failing = [] if report is None else failing_ids(report)
                fail(
                    "cli.1",
                    "package oracle rejects CRLF-terminated otherwise-valid output (failed cases %s)" % failing,
                )

        # ---- cli.2 transcript anchoring --------------------------------
        case_set = None
        if "runnable_cases" in located:
            with open(located["runnable_cases"], "r", encoding="utf-8") as handle:
                try:
                    case_set = json.load(handle)
                except ValueError as error:
                    fail("cli.2", "runnable_cases component is not valid JSON: %s" % error)
            if case_set is not None and not isinstance(case_set, dict):
                fail("cli.2", "runnable_cases component is not a JSON object")
                case_set = None
        if case_set is not None:
            transcripts = load_transcripts()
            anchored = 0
            case_list = case_set.get("cases", [])
            if not isinstance(case_list, list):
                fail("cli.2", "runnable_cases 'cases' is not a list")
                case_list = []
            for case in case_list:
                if not isinstance(case, dict):
                    fail("cli.2", "case record is not a JSON object")
                    continue
                anchor = case.get("anchor")
                if anchor is None:
                    continue
                if not isinstance(anchor, str) or anchor not in transcripts:
                    fail("cli.2", "case '%s' anchors to unknown transcript '%s'" % (case.get("id"), anchor))
                    continue
                if not anchored_case_matches(case, transcripts[anchor]):
                    fail("cli.2", "case '%s' claims anchor '%s' but does not reproduce it" % (case.get("id"), anchor))
                    continue
                anchored += 1
            if anchored == 0:
                reason = str(case_set.get("anchor_impossibility") or "").strip()
                if not reason:
                    fail("cli.2", "no oracle anchored to an exhibited transcript and no impossibility reason recorded")
                elif "implementation artifact" in reason.lower():
                    fail("cli.2", "anchor impossibility reason is 'implementation artifact', which is not acceptable")

        # ---- cli.3 qualification independence --------------------------
        if qualification is not None and "provenance" in located:
            provenance = None
            with open(located["provenance"], "r", encoding="utf-8") as handle:
                try:
                    provenance = json.load(handle)
                except ValueError as error:
                    fail("cli.3", "provenance component is not valid JSON: %s" % error)
            if provenance is not None and not isinstance(provenance, dict):
                fail("cli.3", "provenance component is not a JSON object")
                provenance = None
            builder = "" if provenance is None else str(provenance.get("builder_context") or "").strip()
            if provenance is None:
                pass
            elif not builder:
                fail("cli.3", "provenance records no builder_context")
            else:
                entries = qualification.get("entries")
                for entry in entries if isinstance(entries, list) else []:
                    if not isinstance(entry, dict) or entry.get("required") is not True:
                        continue
                    evidence = entry.get("evidence") or {}
                    context = str(evidence.get("context") or "").strip() if isinstance(evidence, dict) else ""
                    if not context or context == builder:
                        fail(
                            "cli.3",
                            "required verdict '%s' cites only builder self-run evidence (context %r)"
                            % (entry.get("criterion", "<unnamed>"), context or None),
                        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    if failures:
        sys.stderr.write("probe FAIL (%s): %d violation(s)\n" % (impl_dir, len(failures)))
        for line in failures:
            sys.stderr.write("  - %s\n" % line)
        return 1
    sys.stdout.write("probe PASS (%s): 7 checks (P0.a-P0.d, cli.1-cli.3)\n" % impl_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
