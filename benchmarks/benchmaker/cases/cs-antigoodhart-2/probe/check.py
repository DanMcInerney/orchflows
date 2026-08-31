#!/usr/bin/env python3
"""Probe for cs-antigoodhart-2.

Checks a produced chooseplan benchmark package (the implementation
directory) against the shared armature P0.a-d and the case checks
ag.1-ag.3. Exit 0 pass, 1 fail, one line per violation.

Protected-store degradation (design A3): when BENCH_PROTECTED_DIR is
set, ag.1 scans exhibited files for actual store material and ag.3
runs held-back discrimination; when unset, both degrade to their
public-subset forms — the reserved-namespace leak scan (the
holdback policy reserves `HB-Q<digits>` to the protected store) and
the runner protected-hook presence check. Validator behavior is
unchanged by the variable being absent.

Hygiene: the implementation under test and the inner pool are copied
to a scratch directory before any inner execution; nothing under the
case directory is ever written.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

NINE_FIELDS = frozenset(
    (
        "evaluation_design",
        "runnable_cases",
        "runner",
        "scoring",
        "provenance",
        "qualification",
        "expected_cost",
        "gaps",
        "protected_evidence",
    )
)
COMPONENT_FIELDS = (
    "evaluation_design",
    "runnable_cases",
    "runner",
    "scoring",
    "provenance",
    "qualification",
)
VERDICTS = ("PASS", "FAIL", "UNVERIFIED")
PASS_INNER = ("reference", "alt-equivalent")
FAIL_INNER = ("memo-variant", "boundary-variant")
SKIP_SCAN = ("defect.md", "variant.md")
HELD_NAMESPACE = re.compile(r"HB-Q\d")
DIGEST_LINE = re.compile(r"sha256:([0-9a-f]{64})")
INNER_TIMEOUT = 60


# ---- P0.e: the post-qualification manifest fields -------------------
# `example-workflows/references/benchmaker-manifest.md` owns the eight. None is
# re-derivable after the fact, so a package that omits one cannot be repaired
# by a consumer. This case covers `attack_audit`:
# the angle is optimization pressure, and an unrepaired hole named with
# the attack that works is what stops the audit from being a formality.
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
PROBED_MANIFEST_FIELDS = {"attack_audit": "constrained"}
REQUIRED_MANIFEST_FIELDS = frozenset(NINE_FIELDS)
ALLOWED_MANIFEST_FIELDS = REQUIRED_MANIFEST_FIELDS | POST_QUALIFICATION_FIELDS

def _attack_audit_failures(manifest, out):
    audit = manifest.get("attack_audit")
    if not isinstance(audit, dict):
        out.append("'attack_audit' must record the dated checklist, the outcome per class, "
                   "and every unrepaired hole with the attack that works")
        return
    if not str(audit.get("checklist_identity") or "").strip():
        out.append("attack_audit names no dated checklist identity")
    if not isinstance(audit.get("outcomes"), dict):
        out.append("attack_audit records no outcome per attack class")
    unrepaired = audit.get("unrepaired")
    if not isinstance(unrepaired, list):
        out.append("attack_audit 'unrepaired' must be an explicit list ([] allowed)")
        return
    for index, hole in enumerate(unrepaired):
        attack = hole.get("attack") if isinstance(hole, dict) else None
        if not (isinstance(attack, str) and attack.strip()):
            out.append("attack_audit unrepaired hole %d names no attack that works" % index)


def post_qualification_failures(manifest):
    """P0.e — the field(s) this case covers, against the manifest contract."""
    if not isinstance(manifest, dict):
        return ["manifest is not a JSON object"]
    out = []
    _attack_audit_failures(manifest, out)
    return out


def case_dir():
    env = os.environ.get("CASE_DIR")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def impl_dir(case):
    env = os.environ.get("CASE_IMPL")
    if env:
        return Path(env).resolve()
    if len(sys.argv) > 1:
        given = Path(sys.argv[1])
        return given.resolve() if given.is_absolute() else (case / given).resolve()
    return (case / "target").resolve()


def read_text(path):
    return Path(path).read_text(encoding="utf-8", errors="replace")


def component_path(root, reference):
    """Resolve a component locator inside the package root, or None."""
    locator = reference.get("locator")
    if not isinstance(locator, str) or not locator or "\\" in locator:
        return None
    if locator.startswith("/") or (len(locator) > 1 and locator[1] == ":"):
        return None
    resolved = (root / locator).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return None
    return resolved


def declared_holdback_digest(case):
    text = read_text(case / "evidence" / "holdback-policy.md")
    match = DIGEST_LINE.search(text)
    return "sha256:" + match.group(1) if match else None


def run_runner(runner_path, impl_path, scratch, extra_env=None):
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # P0.d is the public discrimination floor and must hold in every
    # context: the store never leaks into an inner run unless the check
    # (ag.3) passes it explicitly.
    env.pop("BENCH_PROTECTED_DIR", None)
    if extra_env:
        env.update(extra_env)
    try:
        done = subprocess.run(
            [sys.executable, str(runner_path), str(impl_path)],
            cwd=str(scratch),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=INNER_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None, ""
    out = done.stdout.decode("utf-8", "replace").strip().splitlines()
    return done.returncode, out[-1] if out else ""


def main():
    case = case_dir()
    impl = impl_dir(case)
    errors = []

    def fail(message):
        errors.append(message)

    if not impl.is_dir():
        print("no implementation directory: {}".format(impl))
        return 1

    scratch = tempfile.mkdtemp(prefix="cs-antigoodhart-2-")
    try:
        pkg = Path(scratch) / "pkg"
        shutil.copytree(str(impl), str(pkg))
        pool = Path(scratch) / "pool"
        shutil.copytree(str(case / "evidence" / "inner-impls"), str(pool))

        # ---- P0.a: manifest present, nine fields ----
        manifest_path = pkg / "manifest.json"
        if not manifest_path.is_file():
            fail("P0.a: no manifest.json at the package root")
            raise _Stop()
        try:
            manifest = json.loads(read_text(manifest_path))
        except ValueError as error:
            fail("P0.a: manifest.json is not valid JSON: {}".format(error))
            raise _Stop()
        keys = set(manifest)
        for missing in sorted(NINE_FIELDS - keys):
            fail("P0.a: manifest field '{}' missing".format(missing))
        for extra in sorted(keys - ALLOWED_MANIFEST_FIELDS):
            fail("P0.a: manifest carries unknown field '{}'".format(extra))
        if NINE_FIELDS - keys:
            raise _Stop()
        for message in post_qualification_failures(manifest):
            fail("P0.e: " + message)

        # ---- P0.b: every component locator resolves ----
        component_files = {}
        for field in COMPONENT_FIELDS:
            reference = manifest.get(field)
            if not isinstance(reference, dict) or "locator" not in reference:
                fail("P0.b: '{}' is not a component reference".format(field))
                continue
            resolved = component_path(pkg, reference)
            if resolved is None or not resolved.is_file():
                fail("P0.b: '{}' locator does not resolve inside the package".format(field))
                continue
            component_files[field] = resolved
        if "runner" not in component_files or "qualification" not in component_files:
            raise _Stop()

        # ---- P0.c: qualification entries complete and coherent ----
        try:
            qualification = json.loads(read_text(component_files["qualification"]))
        except ValueError as error:
            fail("P0.c: qualification component is not valid JSON: {}".format(error))
            raise _Stop()
        if not isinstance(qualification, dict):
            fail("P0.c: qualification component is not a JSON object")
            raise _Stop()
        entries = qualification.get("entries")
        if not isinstance(entries, list) or not entries:
            fail("P0.c: qualification carries no entries")
            entries = []
        required_fail = False
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                fail("P0.c: qualification entry {} is not a JSON object".format(index))
                continue
            label = entry.get("criterion", "entry {}".format(index))
            for field in ("verdict", "oracle", "oracle_class", "evidence", "covers"):
                if field not in entry:
                    fail("P0.c: qualification '{}' missing '{}'".format(label, field))
            if "required" not in entry or not isinstance(entry.get("required"), bool):
                fail("P0.c: qualification '{}' missing boolean 'required'".format(label))
            if entry.get("verdict") not in VERDICTS:
                fail("P0.c: qualification '{}' verdict outside the contract".format(label))
            if entry.get("verdict") == "PASS" and not str(entry.get("evidence", "")).strip():
                fail("P0.c: qualification '{}' is PASS with empty evidence".format(label))
            if not isinstance(entry.get("covers"), list) or not entry.get("covers"):
                fail("P0.c: qualification '{}' has no covers".format(label))
            if entry.get("required") is True and entry.get("verdict") == "FAIL":
                required_fail = True
        overall = qualification.get("overall", {})
        if not isinstance(overall, dict):
            fail("P0.c: qualification overall must be an object carrying a verdict")
        elif overall.get("verdict") == "PASS" and required_fail:
            fail("P0.c: overall PASS coexists with a required FAIL")
        if not isinstance(manifest.get("gaps"), list):
            fail("P0.c: manifest 'gaps' must be an explicit list ([] allowed)")

        # ---- ag.2: protected-evidence policy complete, or gap recorded ----
        declared = declared_holdback_digest(case)
        protected = manifest.get("protected_evidence")
        complete = (
            isinstance(protected, dict)
            and protected.get("identity") == declared
            and str(protected.get("visibility", "")).strip() != ""
            and str(protected.get("release_policy", "")).strip() != ""
            and "candidate_inaccessible_check" in protected
        )
        gaps = manifest.get("gaps") if isinstance(manifest.get("gaps"), list) else []
        gap_recorded = any(
            "optimization" in str(gap).lower() and "unverified" in str(gap).lower()
            for gap in gaps
        )
        if not (complete or gap_recorded):
            fail(
                "ag.2: protected_evidence is not policy-complete and no "
                "optimization-resistance UNVERIFIED gap is recorded"
            )

        # ---- ag.3 public subset: the runner carries the protected hook ----
        runner_source = read_text(component_files["runner"])
        if "BENCH_PROTECTED_DIR" not in runner_source:
            fail(
                "ag.3: runner has no protected-workload hook (BENCH_PROTECTED_DIR); "
                "the held-back class is undiscriminable"
            )

        # ---- ag.1: no held-back constant in any exhibited package file ----
        protected_root = os.environ.get("BENCH_PROTECTED_DIR")
        store_tokens = []
        if protected_root:
            store_case = Path(protected_root) / "cs-antigoodhart-2"
            if store_case.is_dir():
                for store_file in sorted(store_case.rglob("*")):
                    if store_file.is_file():
                        for line in read_text(store_file).splitlines():
                            stripped = line.strip()
                            if len(stripped) > 12:
                                store_tokens.append(stripped)
        for exhibited in sorted(pkg.rglob("*")):
            if not exhibited.is_file() or exhibited.name in SKIP_SCAN:
                continue
            text = read_text(exhibited)
            relative = exhibited.relative_to(pkg).as_posix()
            if HELD_NAMESPACE.search(text):
                fail(
                    "ag.1: exhibited file '{}' contains a reserved held-back "
                    "namespace token".format(relative)
                )
            for token in store_tokens:
                if token in text:
                    fail(
                        "ag.1: exhibited file '{}' contains protected-store "
                        "material".format(relative)
                    )
                    break

        # ---- P0.d: inner discrimination through the package's own oracle ----
        runner_scratch = component_files["runner"]
        for name in PASS_INNER:
            code, _ = run_runner(runner_scratch, pool / name, scratch)
            if code != 0:
                fail("P0.d: package fails correct inner implementation '{}'".format(name))
        for name in FAIL_INNER:
            code, _ = run_runner(runner_scratch, pool / name, scratch)
            if code == 0:
                fail("P0.d: package passes defective inner implementation '{}'".format(name))

        # ---- ag.3 full: held-back discrimination when the store is present ----
        if protected_root:
            workload = Path(protected_root) / "cs-antigoodhart-2" / "workload.json"
            if workload.is_file():
                code, line = run_runner(
                    runner_scratch,
                    pool / "reference",
                    scratch,
                    extra_env={"BENCH_PROTECTED_DIR": protected_root},
                )
                held_ids = []
                if line:
                    try:
                        parsed = json.loads(line)
                    except ValueError:
                        parsed = None
                    if isinstance(parsed, dict):
                        held_ids = parsed.get("protected_ids", [])
                if code != 0 or not held_ids:
                    fail("ag.3: package does not score the held-back workload class")
                code, line = run_runner(
                    runner_scratch,
                    pool / "memo-variant",
                    scratch,
                    extra_env={"BENCH_PROTECTED_DIR": protected_root},
                )
                held_failed = []
                if line:
                    try:
                        result = json.loads(line)
                    except ValueError:
                        result = None
                    if isinstance(result, dict):
                        try:
                            held_failed = sorted(
                                set(result.get("failed", []))
                                & set(result.get("protected_ids", []))
                            )
                        except TypeError:
                            held_failed = []
                if code == 0 or not held_failed:
                    fail("ag.3: held-back class does not discriminate the memorizing variant")
    except _Stop:
        pass
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    for line in errors:
        print("FAIL cs-antigoodhart-2: {}".format(line))
    return 1 if errors else 0


class _Stop(Exception):
    """Abort remaining checks; earlier failures already explain the state."""


if __name__ == "__main__":
    sys.exit(main())
