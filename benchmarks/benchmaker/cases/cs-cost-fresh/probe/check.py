#!/usr/bin/env python3
"""Case-author sanity oracle for cs-cost-fresh. NOT the benchmark.

Usage (from the case directory):

    uv run --no-project python probe/check.py [IMPLEMENTATION]

IMPLEMENTATION is a directory holding a benchmark package (manifest.json
at its root); it may also arrive in ``CASE_IMPL``, and defaults to
``target``. Paths resolve against the caller's directory and then
against this case's own directory, so the probe runs from the case
directory or from the repository root.

Checks (exit 0 all pass, exit 1 with one line per failure):

  P0.a  manifest present, exactly the nine fields.
  P0.b  every component reference's locator resolves to shipped bytes,
        relative to the package root.
  P0.c  qualification entries verdict-contract-complete; no overall
        PASS with a required FAIL; no PASS entry with empty evidence;
        manifest gaps field explicit.
  cp.1  manifest expected_cost present; recorded suite estimate covers
        the selected queries and stays inside the case's declared
        60-query budget. When cp.1 fails the execution sweep is
        skipped: an over-budget suite is not run to prove it.
  cp.2  the selected input set carries at least one witness for each
        of W1, W2, W3 per evidence/witness-classes.md, verified by
        regenerating the corpus at the evidence-fixed parameters and
        evaluating the class predicates; the package's recorded corpus
        parameters must equal the evidence-fixed ones.
  P0.d  inner discrimination: the package's own runner+scoring, run
        against evidence/inner-impls/, passes reference and good
        variants and fails every bad variant including the near miss.
  cp.3  each per-class inner bad (W1, W2, W3) is failed — dropping the
        sparse class is not survivable.

Hygiene: the package, the inner-implementation pool, and the
regenerated corpus live in a scratch directory; nothing under the case
directory is ever written.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True  # the probe never writes inside the case directory

CASE_DIR = Path(__file__).resolve().parent.parent
POOL_DIR = CASE_DIR / "evidence" / "inner-impls"
CORPUS_GEN = CASE_DIR / "evidence" / "corpus-gen.py"
CORPUS_SEED = 20260807
CORPUS_COUNT = 20000
QUERY_BUDGET = 60
SWEEP_BUDGET_S = 120.0
PER_RUN_TIMEOUT_S = 60.0
CLASS_BADS = {"W1": "bad-w1-boundary", "W2": "bad-w2-dupes", "W3": "bad-w3-rollover"}
COMPONENT_KEYS = (
    "evaluation_design",
    "runnable_cases",
    "runner",
    "scoring",
    "provenance",
    "qualification",
)
MANIFEST_KEYS = frozenset(
    COMPONENT_KEYS + ("expected_cost", "gaps", "protected_evidence")
)
ENTRY_KEYS = ("verdict", "oracle", "oracle_class", "evidence", "covers", "required")


# ---- P0.e: the post-qualification manifest fields -------------------
# `compositions/references/benchmaker-manifest.md` owns the eight. None is
# re-derivable after the fact, so a package that omits one cannot be repaired
# by a consumer. This case covers `measurement`:
# a measurement narrowed by a budget must say what it did not reach.
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
PROBED_MANIFEST_FIELDS = {"measurement": "constrained"}
REQUIRED_MANIFEST_FIELDS = frozenset(MANIFEST_KEYS)
ALLOWED_MANIFEST_FIELDS = REQUIRED_MANIFEST_FIELDS | POST_QUALIFICATION_FIELDS

_MEASUREMENT_STATUSES = ("both-pass", "split", "both-fail", "inversion")


def _measurement_failures(manifest, out):
    record = manifest.get("measurement")
    if not isinstance(record, dict):
        out.append("'measurement' must record the pass: candidate identities, measured scope, "
                   "per-case status, distinct failure signatures and the margin")
        return
    if not isinstance(record.get("candidates"), dict) or not record["candidates"]:
        out.append("measurement names no candidate identities")
    if not str(record.get("scope") or "").strip():
        out.append("measurement states no measured scope")
    per_case = record.get("per_case_status")
    if not isinstance(per_case, dict) or not per_case:
        out.append("measurement records no per-case status")
    else:
        for case_id in sorted(per_case):
            if per_case[case_id] not in _MEASUREMENT_STATUSES:
                out.append("measurement status %r for '%s' is outside %s"
                           % (per_case[case_id], case_id, list(_MEASUREMENT_STATUSES)))
    signatures = record.get("distinct_failure_signatures")
    if isinstance(signatures, bool) or not isinstance(signatures, int) or signatures < 0:
        out.append("measurement records no count of distinct failure signatures")
    if "margin_cases" not in record:
        out.append("measurement records no margin")


def post_qualification_failures(manifest):
    """P0.e — the field(s) this case covers, against the manifest contract."""
    if not isinstance(manifest, dict):
        return ["manifest is not a JSON object"]
    out = []
    _measurement_failures(manifest, out)
    return out


def resolve_impl():
    raw = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CASE_IMPL")
    if not raw:
        raw = "target"
    for candidate in (Path(raw), CASE_DIR / raw):
        if candidate.is_dir():
            return candidate.resolve()
    return None


def locate(root, locator):
    """Resolve a component locator inside the package root, or None."""
    if not isinstance(locator, str) or not locator or "\\" in locator:
        return None
    if locator.startswith("/") or (len(locator) > 1 and locator[1] == ":"):
        return None
    resolved = os.path.normpath(os.path.join(str(root), locator))
    base = os.path.normpath(str(root))
    if not (resolved == base or resolved.startswith(base + os.sep)):
        return None
    return Path(resolved)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_manifest(impl, failures):
    """P0.a + P0.b + P0.c. Returns the parsed manifest or None."""
    manifest_path = impl / "manifest.json"
    if not manifest_path.is_file():
        failures.append("P0.a: no manifest.json at the package root")
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except ValueError as error:
        failures.append("P0.a: manifest.json is not valid JSON: %s" % error)
        return None
    if not isinstance(manifest, dict):
        failures.append("P0.a: manifest.json is not a JSON object")
        return None
    keys = set(manifest)
    for missing in sorted(MANIFEST_KEYS - keys):
        failures.append("P0.a: manifest field '%s' missing" % missing)
    for extra in sorted(keys - ALLOWED_MANIFEST_FIELDS):
        failures.append("P0.a: manifest carries unknown field '%s'" % extra)
    if (MANIFEST_KEYS - keys) or (keys - ALLOWED_MANIFEST_FIELDS):
        return None
    for message in post_qualification_failures(manifest):
        failures.append("P0.e: " + message)
    for key in COMPONENT_KEYS:
        ref = manifest.get(key)
        if not (isinstance(ref, dict) and "locator" in ref):
            failures.append("P0.b: component '%s' is not a locator reference" % key)
            continue
        path = locate(impl, ref["locator"])
        if path is None or not path.is_file():
            failures.append(
                "P0.b: component '%s' locator '%s' does not resolve to a file inside the package"
                % (key, ref["locator"])
            )

    if not isinstance(manifest.get("gaps"), list):
        failures.append("P0.c: manifest 'gaps' must be an explicit list ([] allowed)")
    qual_ref = manifest.get("qualification")
    if isinstance(qual_ref, dict):
        qual_path = locate(impl, qual_ref.get("locator", ""))
        if qual_path is not None and qual_path.is_file():
            try:
                qual = json.loads(qual_path.read_text(encoding="utf-8"))
            except ValueError as error:
                failures.append("P0.c: qualification component is not valid JSON: %s" % error)
                qual = None
            if isinstance(qual, dict):
                entries = qual.get("entries")
                if not (isinstance(entries, list) and entries):
                    failures.append("P0.c: qualification carries no entries")
                else:
                    required_fail = False
                    for index, entry in enumerate(entries):
                        if not isinstance(entry, dict):
                            failures.append("P0.c: qualification entry %d is not an object" % index)
                            continue
                        for field in ENTRY_KEYS:
                            if field not in entry:
                                failures.append(
                                    "P0.c: qualification entry %d lacks '%s'" % (index, field)
                                )
                        if entry.get("verdict") == "FAIL" and entry.get("required") is True:
                            required_fail = True
                        if entry.get("verdict") == "PASS" and not str(entry.get("evidence", "")).strip():
                            failures.append(
                                "P0.c: qualification entry %d is PASS with empty evidence" % index
                            )
                    if qual.get("overall") == "PASS" and required_fail:
                        failures.append("P0.c: overall PASS coexists with a required FAIL")
    return manifest


def load_cases(impl, manifest, failures):
    cases_ref = manifest.get("runnable_cases")
    if not isinstance(cases_ref, dict):
        return None
    cases_path = locate(impl, cases_ref.get("locator", ""))
    if cases_path is None or not cases_path.is_file():
        return None  # already failed in P0.b
    try:
        return json.loads(cases_path.read_text(encoding="utf-8"))
    except ValueError as error:
        failures.append("cp.2: runnable cases are not valid JSON: %s" % error)
        return None


def check_budget(manifest, data, failures):
    """cp.1 — returns True when the execution sweep may proceed."""
    cost = manifest.get("expected_cost")
    if not isinstance(cost, dict) or "suite_estimate" not in cost:
        failures.append("cp.1: manifest expected_cost with a suite estimate is required")
        return False
    estimate = cost["suite_estimate"]
    selected = len(data.get("cases", [])) if isinstance(data, dict) else 0
    if not isinstance(estimate, int) or estimate < selected:
        failures.append(
            "cp.1: recorded suite estimate (%r) does not cover the %d selected queries"
            % (estimate, selected)
        )
        return False
    if estimate > QUERY_BUDGET:
        failures.append(
            "cp.1: suite estimate %d exceeds the declared %d-query budget"
            % (estimate, QUERY_BUDGET)
        )
        return False
    return True


def matches(level_of_record, wanted):
    return wanted == "ANY" or level_of_record == wanted


def check_witnesses(data, records, failures):
    """cp.2 — corpus pin plus one witness per class."""
    corpus = data.get("corpus") if isinstance(data, dict) else None
    if not (
        isinstance(corpus, dict)
        and corpus.get("seed") == CORPUS_SEED
        and corpus.get("count") == CORPUS_COUNT
    ):
        failures.append(
            "cp.2: recorded corpus parameters must pin seed %d / count %d"
            % (CORPUS_SEED, CORPUS_COUNT)
        )
        return
    by_ts = {}
    for ts, level, _msg in records:
        by_ts.setdefault(ts, []).append(level)
    witnessed = set()
    for case in data.get("cases", []):
        if not isinstance(case, dict):
            failures.append("cp.2: selected case record is not an object")
            continue
        start, end, level = case.get("start"), case.get("end"), case.get("level")
        if not (isinstance(start, int) and isinstance(end, int) and isinstance(level, str)):
            continue
        if any(matches(lvl, level) for lvl in by_ts.get(start, [])):
            witnessed.add("W1")
        for ts, levels in by_ts.items():
            if start <= ts <= end and sum(1 for lvl in levels if matches(lvl, level)) >= 2:
                witnessed.add("W2")
                break
        if start % 86400 == 0 and any(matches(lvl, level) for lvl in by_ts.get(start, [])):
            witnessed.add("W3")
    for name in ("W1", "W2", "W3"):
        if name not in witnessed:
            failures.append(
                "cp.2: no selected input witnesses class %s per witness-classes.md" % name
            )


def check_discrimination(impl, manifest, corpus_file, failures):
    """P0.d + cp.3 — scratch-copied sweep of the inner pool."""
    scoring_ref = manifest.get("scoring")
    if not isinstance(scoring_ref, dict) or locate(impl, scoring_ref.get("locator", "")) is None:
        return
    scoring_locator = scoring_ref["locator"]
    scratch = Path(tempfile.mkdtemp(prefix="cs-cost-probe-"))
    survivors = []
    try:
        package = scratch / "package"
        shutil.copytree(str(impl), str(package))
        pool = scratch / "pool"
        shutil.copytree(str(POOL_DIR), str(pool))
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        deadline = time.monotonic() + SWEEP_BUDGET_S
        for entry in sorted(pool.iterdir()):
            if not entry.is_dir():
                continue
            expect_pass = entry.name.startswith(("reference", "good"))
            remaining = min(PER_RUN_TIMEOUT_S, deadline - time.monotonic())
            if remaining <= 0:
                failures.append("P0.d: inner sweep exceeded its %.0f s envelope" % SWEEP_BUDGET_S)
                return
            try:
                done = subprocess.run(
                    [
                        sys.executable,
                        str(package / scoring_locator),
                        str(entry),
                        str(corpus_file),
                    ],
                    cwd=str(package),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=remaining,
                )
                code = done.returncode
            except subprocess.TimeoutExpired:
                failures.append("P0.d: scoring '%s' exceeded its time slice" % entry.name)
                continue
            if expect_pass and code != 0:
                failures.append(
                    "P0.d: package scoring fails inner '%s' (exit %d) but it must pass"
                    % (entry.name, code)
                )
            elif not expect_pass and code == 0:
                failures.append(
                    "P0.d: package scoring passes inner '%s' but it must fail" % entry.name
                )
                survivors.append(entry.name)
    finally:
        shutil.rmtree(str(scratch), ignore_errors=True)
    for class_name, bad_name in sorted(CLASS_BADS.items()):
        if bad_name in survivors:
            failures.append(
                "cp.3: the %s-class inner bad '%s' survives — dropping that class is not survivable"
                % (class_name, bad_name)
            )


def main():
    impl = resolve_impl()
    if impl is None:
        sys.stderr.write("probe: no such implementation directory\n")
        return 2
    failures = []
    manifest = check_manifest(impl, failures)
    if manifest is not None:
        data = load_cases(impl, manifest, failures)
        sweep_allowed = check_budget(manifest, data, failures)
        if data is not None and sweep_allowed and not any(f.startswith("P0.b") for f in failures):
            generator = load_module("corpus_generator", CORPUS_GEN)
            records = generator.generate(CORPUS_SEED, CORPUS_COUNT)
            check_witnesses(data, records, failures)
            scratch_corpus = Path(tempfile.mkdtemp(prefix="cs-cost-corpus-")) / "corpus.log"
            try:
                with open(str(scratch_corpus), "w", encoding="utf-8", newline="\n") as handle:
                    for ts, level, msg in records:
                        handle.write("%d %s %s\n" % (ts, level, msg))
                check_discrimination(impl, manifest, scratch_corpus, failures)
            finally:
                shutil.rmtree(str(scratch_corpus.parent), ignore_errors=True)
    if failures:
        sys.stderr.write("probe FAIL (%s): %d violation(s)\n" % (impl.name, len(failures)))
        for failure in failures:
            sys.stderr.write("  - %s\n" % failure)
        return 1
    sys.stdout.write("probe PASS (%s)\n" % impl.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
