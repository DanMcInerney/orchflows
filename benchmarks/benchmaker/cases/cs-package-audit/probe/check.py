#!/usr/bin/env python3
"""Case probe for cs-package-audit. Qualify-the-qualifier.

Independent recomputation over a sealed benchmark package for the
unit-converter target:

  P0.a  manifest present, ten fields, benchmark_identity recomputes
        from the canonical payload
  P0.b  every component reference's sha256 verifies over the shipped
        bytes at its locator (layout-agnostic, package-root relative)
  P0.c  every qualification entry carries verdict/oracle/oracle_class/
        evidence/covers plus a required flag; no overall PASS with a
        required FAIL; no PASS with empty evidence
  P0.d  inner discrimination: the package's own runner + scoring,
        executed against evidence/inner-impls/, pass the reference and
        every good variant and fail every bad variant incl. the
        near-miss
  pa.1  all seven qualification axes present and contract-complete;
        no verdict value outside the contract (A6: the recorded set is
        checked as-is)
  pa.2  no verdict's evidence provenance is builder-only: the
        qualifying context differs from the builder context recorded
        in provenance, and every entry's evidence is attributable to it
  pa.3  seed discipline: an inert bad variant with a behavior-change
        proof; every counted bad proven behavior-changing; exclusions
        carry equivalence proofs; inert-shown-equivalent (if present)
        appears as a gap with discrimination UNVERIFIED
  pa.4  every inner case's provenance parses as synthesis-claim
        tracing or an evidence-identity citation, never a pointer to
        its own expected answers
  pa.5  expected and actual qualification spend recorded; exactly one
        benchmark identity in the implementation

Usage: check.py [IMPL_DIR]. CASE_IMPL outranks the positional. The
implementation and the inner pool are copied to a scratch directory
before any execution; nothing under the case directory is written.
Exit 0 when every check passes, else 1 with one FAIL line per finding.

Stdlib only. Python 3.9+.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CASE_ROOT = Path(__file__).resolve().parent.parent
AXES = ("failability", "coverage", "discrimination", "reproducibility",
        "redundancy", "provenance", "execution-cost")
MANIFEST_FIELDS = (
    "benchmark_identity", "evaluation_design", "runnable_cases", "runner",
    "scoring", "provenance", "qualification", "expected_cost", "gaps",
    "protected_evidence",
)
COMPONENTS = (
    "evaluation_design", "runnable_cases", "runner", "scoring",
    "provenance", "qualification",
)
ENTRY_FIELDS = ("verdict", "oracle", "oracle_class", "evidence", "covers", "required")
VERDICTS = ("PASS", "FAIL", "UNVERIFIED")
PROV_SYNTH = re.compile(r"^synthesis@[0-9a-f]{6,}\s+claims\s+[0-9]")
PROV_EVID = re.compile(r"^evidence@sha256:[0-9a-f]{8,}")


def emit(message):
    print(("FAIL " + message).encode("ascii", "replace").decode("ascii"))


def resolve(argument):
    argument = os.environ.get("CASE_IMPL") or argument
    if argument is None or argument == "{target}":
        return CASE_ROOT / "target"
    candidate = Path(argument)
    if candidate.is_absolute():
        return candidate
    for base in (Path.cwd(), CASE_ROOT):
        if (base / candidate).exists():
            return base / candidate
    return Path.cwd() / candidate


def read(path):
    return path.read_text(encoding="utf-8")


def load_json(path, label, failures):
    try:
        return json.loads(read(path))
    except (OSError, ValueError) as error:
        failures.append("%s does not parse: %s" % (label, error))
        return None


def canonical_identity(manifest):
    payload = {k: v for k, v in manifest.items() if k != "benchmark_identity"}
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(canon).hexdigest()


def component_path(pkg, manifest, name):
    ref = manifest.get(name)
    if isinstance(ref, dict) and isinstance(ref.get("locator"), str):
        return (pkg / ref["locator"]).resolve()
    return None


def check_seal(pkg, failures):
    manifest_path = pkg / "manifest.json"
    if not manifest_path.is_file():
        failures.append("P0.a: no package/manifest.json")
        return None
    manifest = load_json(manifest_path, "P0.a: manifest.json", failures)
    if manifest is None:
        return None
    missing = [f for f in MANIFEST_FIELDS if f not in manifest]
    for field in missing:
        failures.append("P0.a: manifest is missing field '%s'" % field)
    if missing:
        return manifest
    if manifest["benchmark_identity"] != canonical_identity(manifest):
        failures.append("P0.a: benchmark_identity does not recompute from the canonical payload")
    if not isinstance(manifest["gaps"], list):
        failures.append("P0.a: manifest gaps must be an explicit list")
    for name in COMPONENTS:
        ref = manifest[name]
        if not (isinstance(ref, dict) and isinstance(ref.get("sha256"), str)
                and isinstance(ref.get("locator"), str)):
            failures.append("P0.b: component '%s' lacks sha256 + locator" % name)
            continue
        resolved = (pkg / ref["locator"]).resolve()
        if not resolved.is_file():
            failures.append("P0.b: component '%s' locator '%s' resolves to no file"
                            % (name, ref["locator"]))
            continue
        digest = "sha256:" + hashlib.sha256(resolved.read_bytes()).hexdigest()
        if digest != ref["sha256"]:
            failures.append("P0.b: component '%s' bytes do not match the recorded digest" % name)
    return manifest


def check_qual_shape(record, failures):
    entries = record.get("entries")
    if not isinstance(entries, list) or not entries:
        failures.append("P0.c: qualification carries no entries list")
        return {}
    by_criterion = {}
    required_fail = False
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            failures.append("P0.c: entry %d is not an object" % index)
            continue
        for field in ENTRY_FIELDS:
            if field not in entry:
                failures.append("P0.c: entry %d lacks '%s'" % (index, field))
        verdict = entry.get("verdict")
        if verdict not in VERDICTS:
            failures.append("P0.c: entry %d verdict %r outside the contract" % (index, verdict))
        if verdict == "PASS" and not str(entry.get("evidence") or "").strip():
            failures.append("P0.c: entry %d is PASS with empty evidence" % index)
        if verdict == "FAIL" and entry.get("required") is True:
            required_fail = True
        criterion = entry.get("criterion")
        if isinstance(criterion, str):
            by_criterion[criterion] = entry
    if record.get("overall") == "PASS" and required_fail:
        failures.append("P0.c: overall PASS coexists with a required FAIL")
    return by_criterion


def check_axes(by_criterion, failures):
    for axis in AXES:
        if axis not in by_criterion:
            failures.append("pa.1: qualification axis '%s' is absent" % axis)


def check_independence(qual, provenance, failures):
    builder = str((provenance or {}).get("builder_context") or "").strip()
    if not builder:
        failures.append("pa.2: provenance records no builder context")
    qual_ctx = str(qual.get("context") or "").strip()
    if not qual_ctx:
        failures.append("pa.2: qualification records no qualifying context id")
        return
    if builder and qual_ctx == builder:
        failures.append("pa.2: qualifying context equals the builder context; every verdict is builder-only")
    for index, entry in enumerate(qual.get("entries") or []):
        if not isinstance(entry, dict):
            continue
        evidence = str(entry.get("evidence") or "")
        if qual_ctx not in evidence:
            failures.append("pa.2: entry %d evidence is not attributable to the qualifying context" % index)


def check_seed_discipline(qual, manifest, by_criterion, failures):
    sweep = qual.get("seed_sweep")
    if not isinstance(sweep, dict):
        failures.append("pa.3: qualification records no seed sweep")
        return
    seeds = sweep.get("seeds")
    if not isinstance(seeds, list) or not seeds:
        failures.append("pa.3: seed sweep lists no seeds")
        return
    goods = [s for s in seeds if isinstance(s, dict) and s.get("role") == "good"]
    bads = [s for s in seeds if isinstance(s, dict) and s.get("role") == "bad"]
    if not goods:
        failures.append("pa.3: sweep records no known-good seed")
    if not bads:
        failures.append("pa.3: sweep records no known-bad seed")
    inert_found = False
    for seed in bads:
        name = seed.get("name", "?")
        if not str(seed.get("behavior_change_proof") or "").strip():
            failures.append("pa.3: bad seed '%s' counted without a behavior-change proof" % name)
        if seed.get("inert") is True:
            inert_found = True
        if seed.get("shown_equivalent") is True:
            gaps = manifest.get("gaps") if isinstance(manifest, dict) else []
            mentioned = any(name in str(gap) for gap in (gaps or []))
            if not mentioned:
                failures.append("pa.3: inert-shown-equivalent '%s' is not recorded as a gap" % name)
            disc = by_criterion.get("discrimination", {})
            if disc.get("verdict") != "UNVERIFIED":
                failures.append("pa.3: inert-shown-equivalent without discrimination UNVERIFIED")
    if not inert_found:
        failures.append("pa.3: no inert bad variant in the recorded sweep")
    for excluded in sweep.get("excluded") or []:
        if not isinstance(excluded, dict):
            continue
        if not str(excluded.get("equivalence_proof") or "").strip():
            failures.append("pa.3: excluded variant '%s' has no equivalence proof"
                            % excluded.get("name", "?"))


def check_case_provenance(cases, failures):
    for case in (cases or {}).get("cases", []):
        cid = case.get("id", "?")
        prov = str(case.get("provenance") or "").strip()
        if "expected.md" in prov:
            failures.append("pa.4: case '%s' provenance points at its own expected answers" % cid)
            continue
        if not (PROV_SYNTH.match(prov) or PROV_EVID.match(prov)):
            failures.append("pa.4: case '%s' provenance parses as neither claim tracing nor an evidence citation" % cid)


def check_spend_and_identity(impl, qual, failures):
    spend = qual.get("spend")
    if not isinstance(spend, dict) or not str(spend.get("expected") or "").strip() \
            or not str(spend.get("actual") or "").strip():
        failures.append("pa.5: expected and actual qualification spend are not both recorded")
    identities = 0
    for path in sorted(impl.rglob("*.json")):
        data = load_json(path, "pa.5: %s" % path.name, failures)
        identities += count_key(data, "benchmark_identity")
    if identities != 1:
        failures.append("pa.5: found %d benchmark identities; law is exactly one" % identities)


def count_key(node, key):
    total = 0
    if isinstance(node, dict):
        for name, value in node.items():
            if name == key:
                total += 1
            total += count_key(value, key)
    elif isinstance(node, list):
        for value in node:
            total += count_key(value, key)
    return total


def check_inner_discrimination(pkg, manifest, inner_root, failures):
    runner = component_path(pkg, manifest, "runner")
    scoring_path = component_path(pkg, manifest, "scoring")
    if runner is None or not runner.is_file():
        failures.append("P0.d: runner component is not runnable")
        return
    scoring = load_json(scoring_path, "P0.d: scoring", failures) if scoring_path and scoring_path.is_file() else None
    if not isinstance(scoring, dict) or not isinstance(scoring.get("required"), list):
        failures.append("P0.d: scoring names no required case set")
        return
    required = scoring["required"]
    pools = sorted(p for p in inner_root.iterdir() if p.is_dir())
    if not pools:
        failures.append("P0.d: no inner implementations supplied")
        return
    for pool in pools:
        name = pool.name
        expected_pass = name == "reference" or name.startswith("good")
        try:
            done = subprocess.run(
                [sys.executable, "-B", str(runner), str(pool)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            failures.append("P0.d: runner failed against '%s': %s" % (name, error))
            continue
        if done.returncode != 0:
            failures.append("P0.d: runner exited %d against '%s'" % (done.returncode, name))
            continue
        try:
            results = json.loads(done.stdout.decode("utf-8", "replace"))
        except ValueError:
            failures.append("P0.d: runner emitted no parseable results for '%s'" % name)
            continue
        overall = all(
            isinstance(results.get(cid), dict) and results[cid].get("ok") is True
            for cid in required
        )
        if overall != expected_pass:
            failures.append("P0.d: inner '%s' %s but must %s"
                            % (name, "passed" if overall else "failed",
                               "pass" if expected_pass else "fail"))


def audit(impl, inner_root):
    failures = []
    pkg = impl / "package"
    if not pkg.is_dir():
        failures.append("P0.a: no package/ tree")
        return failures
    manifest = check_seal(pkg, failures)
    if manifest is None:
        return failures
    qual_path = component_path(pkg, manifest, "qualification")
    prov_path = component_path(pkg, manifest, "provenance")
    cases_path = component_path(pkg, manifest, "runnable_cases")
    qual = load_json(qual_path, "P0.c: qualification", failures) \
        if qual_path and qual_path.is_file() else None
    provenance = load_json(prov_path, "pa.2: provenance", failures) \
        if prov_path and prov_path.is_file() else None
    cases = load_json(cases_path, "pa.4: cases", failures) \
        if cases_path and cases_path.is_file() else None
    if isinstance(qual, dict):
        by_criterion = check_qual_shape(qual, failures)
        check_axes(by_criterion, failures)
        check_independence(qual, provenance if isinstance(provenance, dict) else {}, failures)
        check_seed_discipline(qual, manifest, by_criterion, failures)
        check_spend_and_identity(impl, qual, failures)
    else:
        failures.append("P0.c: no qualification component")
    if isinstance(cases, dict):
        check_case_provenance(cases, failures)
    else:
        failures.append("pa.4: no runnable cases component")
    check_inner_discrimination(pkg, manifest, inner_root, failures)
    return failures


def main(argv):
    if len(argv) > 2:
        emit("usage: check.py [IMPL_DIR]")
        return 2
    source = resolve(argv[1] if len(argv) == 2 else None)
    if not source.is_dir():
        emit("no such implementation directory: %s" % source)
        return 2
    inner_source = CASE_ROOT / "evidence" / "inner-impls"
    scratch = tempfile.mkdtemp(prefix="cs-package-audit-")
    try:
        impl = Path(scratch) / "impl"
        shutil.copytree(str(source), str(impl))
        inner_root = Path(scratch) / "inner-impls"
        if inner_source.is_dir():
            shutil.copytree(str(inner_source), str(inner_root))
        else:
            emit("case evidence/inner-impls is missing")
            return 2
        failures = audit(impl, inner_root)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    for failure in failures:
        emit(failure)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
