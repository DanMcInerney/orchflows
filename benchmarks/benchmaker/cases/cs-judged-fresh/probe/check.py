#!/usr/bin/env python3
"""Probe for cs-judged-fresh — P0.a-P0.d plus jd.1-jd.3.

The implementation under test is a benchmark package directory (the
reference under target/ or a whole-package seed variant). Judged
criteria are checked for STRUCTURE only — anchors present and
resolving, secondary status, recorded rerun variance, non-compensating
aggregation. The probe never re-judges content, so every check here is
deterministic.

Hygiene: the package and the inner-impl pool are copied to a scratch
directory before any execution; nothing under the case directory is
ever written.

Invocation: uv run --no-project python probe/check.py {impl}
Exit 0 pass; exit 1 with one line per violation.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

CASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_FIELDS = {
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
SOURCE_ID = re.compile(r"^(m\d-\d{2}):", re.M)


def resolve_impl():
    raw = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CASE_IMPL") or "target"
    for candidate in (raw, os.path.join(CASE_DIR, raw)):
        if os.path.isdir(candidate):
            return os.path.abspath(candidate)
    return None


def sha256_path(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_identity(manifest):
    payload = {k: v for k, v in manifest.items() if k != "benchmark_identity"}
    data = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(data.encode("utf-8")).hexdigest()


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def source_ids():
    ids = set()
    directory = os.path.join(CASE_DIR, "evidence", "sources")
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".md"):
            continue
        with open(os.path.join(directory, name), encoding="utf-8") as fh:
            ids.update(SOURCE_ID.findall(fh.read()))
    return ids


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
    if set(manifest) != MANIFEST_FIELDS:
        fails.append(
            "P0.a: manifest fields differ from the ten required (delta: %s)"
            % sorted(set(manifest) ^ MANIFEST_FIELDS)
        )
        return manifest
    if manifest.get("benchmark_identity") != canonical_identity(manifest):
        fails.append("P0.a: benchmark_identity does not recompute from the canonical payload")
    if not isinstance(manifest.get("gaps"), list):
        fails.append("P0.a: manifest 'gaps' must be an explicit list")
    return manifest


def check_p0b(pkg, manifest, fails):
    for name in COMPONENTS:
        ref = manifest.get(name)
        if not isinstance(ref, dict) or "sha256" not in ref or "locator" not in ref:
            fails.append("P0.b: component '%s' lacks sha256 + locator" % name)
            continue
        path = os.path.join(pkg, ref["locator"])
        if not os.path.isfile(path):
            fails.append("P0.b: component '%s' locator '%s' missing" % (name, ref["locator"]))
            continue
        if sha256_path(path) != ref["sha256"]:
            fails.append("P0.b: component '%s' digest mismatch at '%s'" % (name, ref["locator"]))


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
    entries = qual.get("entries")
    if not isinstance(entries, list) or not entries:
        fails.append("P0.c: qualification carries no entries")
        return qual
    required_fail = False
    for entry in entries:
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


def run_scoring(scratch_pkg, manifest, results_path, fails, label):
    scoring = os.path.join(scratch_pkg, manifest["scoring"]["locator"])
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        done = subprocess.run(
            [sys.executable, scoring, results_path],
            cwd=scratch_pkg,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=INNER_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        fails.append("%s: scoring did not run: %s" % (label, error))
        return None
    if done.returncode != 0:
        fails.append("%s: scoring exited %d" % (label, done.returncode))
        return None
    return done.stdout.decode("utf-8", "replace").strip()


def check_p0d(scratch, scratch_pkg, manifest, fails):
    pool = os.path.join(scratch, "inner-impls")
    runner = os.path.join(scratch_pkg, manifest["runner"]["locator"])
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
        verdict = run_scoring(scratch_pkg, manifest, results_path, fails, "P0.d")
        if verdict is None:
            continue
        if name.startswith("bad") and verdict != "FAIL":
            fails.append("P0.d: inner bad variant '%s' was not failed (verdict %r)" % (name, verdict))
        if not name.startswith("bad") and verdict != "PASS":
            fails.append("P0.d: inner variant '%s' did not pass (verdict %r)" % (name, verdict))


def check_jd1(pkg, manifest, qual, fails):
    suite = load_json(os.path.join(pkg, manifest["runnable_cases"]["locator"]))
    judged_ids = [c["id"] for c in suite.get("judged", [])]
    if not judged_ids:
        fails.append("jd.1: package declares no judged criteria")
        return
    prov = load_json(os.path.join(pkg, manifest["provenance"]["locator"]))
    sealed_at = prov.get("sealed_at", "")
    if not sealed_at:
        fails.append("jd.1: provenance carries no sealed_at timestamp")
    variance = (qual or {}).get("judge_variance")
    if not isinstance(variance, list) or not variance:
        fails.append("jd.1: no judge rerun variance record in the qualification component")
        return
    recorded = {v.get("criterion"): v for v in variance}
    for cid in judged_ids:
        entry = recorded.get(cid)
        if entry is None:
            fails.append("jd.1: judged criterion '%s' has no variance record" % cid)
            continue
        reruns = entry.get("reruns", 0)
        scores = entry.get("scores", [])
        if not isinstance(reruns, int) or reruns < 3 or len(scores) != reruns:
            fails.append("jd.1: variance for '%s' lacks >=3 recorded reruns" % cid)
        if not entry.get("covers"):
            fails.append("jd.1: variance for '%s' covers nothing" % cid)
        if sealed_at and not (str(entry.get("recorded_at", "")) < sealed_at):
            fails.append("jd.1: variance for '%s' was not recorded before the seal" % cid)


def check_jd2(pkg, scratch, scratch_pkg, manifest, fails):
    suite = load_json(os.path.join(pkg, manifest["runnable_cases"]["locator"]))
    for crit in suite.get("judged", []):
        if crit.get("secondary") is not True:
            fails.append("jd.2: judged criterion '%s' is not marked secondary" % crit.get("id"))
    det = suite.get("deterministic", [])
    required = [c for c in det if c.get("required")]
    if not required:
        fails.append("jd.2: no required deterministic criterion declared")
        return
    synthetic = []
    first = True
    for crit in det:
        synthetic.append(
            {
                "id": crit["id"],
                "class": "deterministic",
                "required": bool(crit.get("required")),
                "verdict": "FAIL" if (first and crit.get("required")) else "PASS",
            }
        )
        if first and crit.get("required"):
            first = False
    for crit in suite.get("judged", []):
        top = max(crit.get("scale", [2]))
        synthetic.append(
            {"id": crit["id"], "class": "judged", "secondary": True, "required": False, "score": top}
        )
    path = os.path.join(scratch, "synthetic-results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(synthetic, fh)
    verdict = run_scoring(scratch_pkg, manifest, path, fails, "jd.2")
    if verdict is not None and verdict != "FAIL":
        fails.append(
            "jd.2: a required deterministic FAIL with maximal judged scores aggregates to %r, not FAIL"
            % verdict
        )


def check_jd3(pkg, manifest, fails):
    suite = load_json(os.path.join(pkg, manifest["runnable_cases"]["locator"]))
    ids = source_ids()
    for crit in suite.get("judged", []):
        anchors = crit.get("anchors", [])
        if len(anchors) < 2:
            fails.append("jd.3: judged criterion '%s' carries fewer than 2 anchors" % crit.get("id"))
            continue
        levels = set(a.get("level") for a in anchors)
        if len(levels) < 2:
            fails.append("jd.3: anchors for '%s' do not span 2 scale levels" % crit.get("id"))
        for anchor in anchors:
            cite = anchor.get("cite", "")
            if cite not in ids:
                fails.append(
                    "jd.3: anchor for '%s' cites '%s', which is not a source line id"
                    % (crit.get("id"), cite)
                )


def main():
    impl = resolve_impl()
    if impl is None:
        sys.stderr.write("probe: no such implementation directory\n")
        return 2
    fails = []
    manifest = check_p0a(impl, fails)
    if manifest is None or set(manifest) != MANIFEST_FIELDS:
        for line in fails:
            sys.stderr.write("probe FAIL: %s\n" % line)
        return 1
    check_p0b(impl, manifest, fails)
    qual = check_p0c(impl, manifest, fails)
    structural_broken = bool(fails)

    try:
        check_jd1(impl, manifest, qual, fails)
        check_jd3(impl, manifest, fails)
    except (OSError, ValueError, KeyError) as error:
        fails.append("jd: package component unreadable: %s" % error)

    if not structural_broken:
        scratch = tempfile.mkdtemp(prefix="cs-judged-probe-")
        try:
            scratch_pkg = os.path.join(scratch, "pkg")
            shutil.copytree(impl, scratch_pkg)
            shutil.copytree(
                os.path.join(CASE_DIR, "evidence", "inner-impls"),
                os.path.join(scratch, "inner-impls"),
            )
            try:
                check_jd2(impl, scratch, scratch_pkg, manifest, fails)
            except (OSError, ValueError, KeyError) as error:
                fails.append("jd.2: %s" % error)
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
