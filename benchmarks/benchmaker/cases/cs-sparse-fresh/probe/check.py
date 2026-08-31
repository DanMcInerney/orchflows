#!/usr/bin/env python3
"""Probe for cs-sparse-fresh — P0.a-P0.d plus sp.1-sp.3.

The implementation under test is a benchmark package directory. The
licensed behavior set is derived from the case's own evidence: the
documenting line ids of evidence/spec.md. Hygiene: the package and the
inner-impl pool are copied to a scratch directory before any
execution; nothing under the case directory is ever written.

Invocation: uv run --no-project python probe/check.py {impl}
Exit 0 pass; exit 1 with one line per violation.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

CASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_FIELDS = {
    "evaluation_design",
    "runnable_cases",
    "runner",
    "scoring",
    "provenance",
    "qualification",
    "expected_cost",
    "gaps",
    "protected_evidence",
}
COMPONENTS = (
    "evaluation_design",
    "runnable_cases",
    "runner",
    "scoring",
    "provenance",
    "qualification",
)
ENTRY_KEYS = {"verdict", "oracle", "oracle_class", "evidence", "covers", "required"}
INNER_TIMEOUT = 60
SPEC_ID = re.compile(r"^([LE]\d{2}):", re.M)

# The licensed rule set: behavior -> the spec.md line id that documents it.
LICENSED = {
    "key-syntax": "L03",
    "value-type": "L05",
    "comment": "L07",
    "section-header": "L09",
}


# ---- P0.e: the post-qualification manifest fields -------------------
# `example-workflows/references/benchmaker-manifest.md` owns the eight. None is
# re-derivable after the fact, so a package that omits one cannot be repaired
# by a consumer. This case covers `anchors`:
# sparse evidence is exactly when a case has no anchor, so the declared
# `none` with a reason is the branch that matters.
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
PROBED_MANIFEST_FIELDS = {"anchors": "constrained"}
REQUIRED_MANIFEST_FIELDS = frozenset(MANIFEST_FIELDS)
ALLOWED_MANIFEST_FIELDS = REQUIRED_MANIFEST_FIELDS | POST_QUALIFICATION_FIELDS

def schema_ok(manifest):
    keys = set(manifest)
    return not (REQUIRED_MANIFEST_FIELDS - keys) and not (keys - ALLOWED_MANIFEST_FIELDS)


def schema_delta(manifest):
    keys = set(manifest)
    return (REQUIRED_MANIFEST_FIELDS - keys) | (keys - ALLOWED_MANIFEST_FIELDS)

def _anchor_failures(manifest, out):
    anchors = manifest.get("anchors")
    if not isinstance(anchors, dict) or not anchors:
        out.append("'anchors' must bind each case to a reference outside the package")
        return
    for case_id in sorted(anchors):
        value = anchors[case_id]
        text = value.strip() if isinstance(value, str) else ""
        if not text:
            out.append("anchors['%s'] is silent; a declared 'none' is legal, silence is not" % case_id)
        elif text[:4].lower() == "none" and not text[4:].strip(" -—:,.;").strip():
            out.append("anchors['%s'] declares 'none' with no reason" % case_id)


def post_qualification_failures(manifest):
    """P0.e — the field(s) this case covers, against the manifest contract."""
    if not isinstance(manifest, dict):
        return ["manifest is not a JSON object"]
    out = []
    _anchor_failures(manifest, out)
    return out


def resolve_impl():
    raw = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CASE_IMPL") or "target"
    for candidate in (raw, os.path.join(CASE_DIR, raw)):
        if os.path.isdir(candidate):
            return os.path.abspath(candidate)
    return None


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def spec_ids():
    with open(os.path.join(CASE_DIR, "evidence", "spec.md"), encoding="utf-8") as fh:
        return set(SPEC_ID.findall(fh.read()))


def check_p0a(pkg, fails):
    path = os.path.join(pkg, "manifest.json")
    if not os.path.isfile(path):
        fails.append("P0.a: no manifest.json in the package")
        return None
    try:
        manifest = load_json(path)
    except (ValueError, OSError) as error:
        fails.append("P0.a: manifest.json unreadable: %s" % error)
        return None
    if not schema_ok(manifest):
        fails.append(
            "P0.a: manifest fields are outside the schema (delta: %s)"
            % sorted(schema_delta(manifest))
        )
        return manifest
    if not isinstance(manifest.get("gaps"), list):
        fails.append("P0.a: manifest 'gaps' must be an explicit list")
    for message in post_qualification_failures(manifest):
        fails.append("P0.e: " + message)
    return manifest


def check_p0b(pkg, manifest, fails):
    for name in COMPONENTS:
        ref = manifest.get(name)
        if not isinstance(ref, dict) or "locator" not in ref:
            fails.append("P0.b: component '%s' is not a locator reference" % name)
            continue
        path = os.path.join(pkg, ref["locator"])
        if not os.path.isfile(path):
            fails.append("P0.b: component '%s' locator '%s' missing" % (name, ref["locator"]))


def check_p0c(pkg, manifest, fails):
    ref = manifest.get("qualification")
    if not isinstance(ref, dict) or "locator" not in ref:
        return None
    path = os.path.join(pkg, ref["locator"])
    if not os.path.isfile(path):
        return None
    try:
        qual = load_json(path)
    except (ValueError, OSError) as error:
        fails.append("P0.c: qualification unreadable: %s" % error)
        return None
    if not isinstance(qual, dict):
        fails.append("P0.c: qualification component is not a JSON object")
        return None
    entries = qual.get("entries")
    if not isinstance(entries, list) or not entries:
        fails.append("P0.c: qualification carries no entries")
        return qual
    required_fail = False
    for entry in entries:
        if not isinstance(entry, dict):
            fails.append("P0.c: qualification entry is not a JSON object")
            continue
        missing = ENTRY_KEYS - set(entry)
        if missing:
            fails.append("P0.c: entry '%s' missing %s" % (entry.get("criterion", "?"), sorted(missing)))
            continue
        if entry["verdict"] == "FAIL" and entry["required"]:
            required_fail = True
        if entry["verdict"] == "PASS" and not str(entry["evidence"]).strip():
            fails.append("P0.c: PASS entry '%s' has empty evidence" % entry.get("criterion", "?"))
        if not entry["covers"]:
            fails.append("P0.c: entry '%s' has empty covers" % entry.get("criterion", "?"))
    if qual.get("overall") == "PASS" and required_fail:
        fails.append("P0.c: overall PASS coexists with a required FAIL")
    if "gaps" not in qual:
        fails.append("P0.c: qualification 'gaps' field is not explicit")
    return qual


def check_p0d(scratch, scratch_pkg, manifest, fails):
    pool = os.path.join(scratch, "inner-impls")
    runner = os.path.join(scratch_pkg, manifest["runner"]["locator"])
    scoring = os.path.join(scratch_pkg, manifest["scoring"]["locator"])
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for name in sorted(os.listdir(pool)):
        impl = os.path.join(pool, name)
        if not os.path.isdir(impl):
            continue
        try:
            done = subprocess.run(
                [sys.executable, runner, impl],
                cwd=scratch_pkg,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=INNER_TIMEOUT,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            fails.append("P0.d: runner did not run on '%s': %s" % (name, error))
            continue
        if done.returncode != 0:
            fails.append("P0.d: runner exited %d on '%s'" % (done.returncode, name))
            continue
        results_path = os.path.join(scratch, "results-%s.json" % name)
        with open(results_path, "wb") as fh:
            fh.write(done.stdout)
        try:
            scored = subprocess.run(
                [sys.executable, scoring, results_path],
                cwd=scratch_pkg,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=INNER_TIMEOUT,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            fails.append("P0.d: scoring did not run on '%s': %s" % (name, error))
            continue
        verdict = scored.stdout.decode("utf-8", "replace").strip()
        if name.startswith("bad") and verdict != "FAIL":
            fails.append("P0.d: inner bad variant '%s' was not failed (verdict %r)" % (name, verdict))
        if not name.startswith("bad") and verdict != "PASS":
            fails.append("P0.d: inner variant '%s' did not pass (verdict %r)" % (name, verdict))


def check_sp(pkg, manifest, fails):
    suite = load_json(os.path.join(pkg, manifest["runnable_cases"]["locator"]))
    known = spec_ids()
    documenting = set(LICENSED.values())
    for case in suite.get("cases", []):
        rule = case.get("rule", "")
        cites = case.get("cites", "")
        if rule not in LICENSED:
            fails.append(
                "sp.3: case '%s' asserts semantics for '%s', which the spec leaves undocumented"
                % (case.get("id", "?"), rule)
            )
            continue
        cited = cites.split("#", 1)[1] if "#" in cites else ""
        if cited not in known:
            fails.append("sp.1: case '%s' cites '%s', which does not exist" % (case.get("id", "?"), cites))
        elif cited not in documenting or cited != LICENSED[rule]:
            fails.append(
                "sp.1: case '%s' cites '%s', which does not document behavior '%s'"
                % (case.get("id", "?"), cites, rule)
            )
    gaps = manifest.get("gaps") or []
    if not gaps:
        fails.append("sp.2: the package gap register is empty despite partial evidence coverage")
    for gap in gaps:
        if any(doc_id in str(gap) for doc_id in documenting):
            fails.append("sp.2: gap entry overlaps a cased behavior: %r" % gap)


def main():
    impl = resolve_impl()
    if impl is None:
        sys.stderr.write("probe: no such implementation directory\n")
        return 2
    fails = []
    manifest = check_p0a(impl, fails)
    if manifest is None or not schema_ok(manifest):
        for line in fails:
            sys.stderr.write("probe FAIL: %s\n" % line)
        return 1
    check_p0b(impl, manifest, fails)
    check_p0c(impl, manifest, fails)
    structural_broken = bool(fails)

    try:
        check_sp(impl, manifest, fails)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        fails.append("sp: package component unreadable: %s" % error)

    if not structural_broken:
        scratch = tempfile.mkdtemp(prefix="cs-sparse-probe-")
        try:
            scratch_pkg = os.path.join(scratch, "pkg")
            shutil.copytree(impl, scratch_pkg)
            shutil.copytree(
                os.path.join(CASE_DIR, "evidence", "inner-impls"),
                os.path.join(scratch, "inner-impls"),
            )
            check_p0d(scratch, scratch_pkg, manifest, fails)
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    if fails:
        sys.stderr.write("probe FAIL (%s): %d violation(s)\n" % (impl, len(fails)))
        for line in fails:
            sys.stderr.write("  - %s\n" % line)
        return 1
    sys.stdout.write("probe PASS (%s)\n" % impl)
    return 0


if __name__ == "__main__":
    sys.exit(main())
