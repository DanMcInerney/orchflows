#!/usr/bin/env python3
"""Probe for cs-workflow-fresh — P0.a-P0.d plus wf.1-wf.6.

Invoked per the case's probe key:

    uv run --no-project python probe/check.py {impl}

cwd is the case directory; {impl} is target/ or one seeds/* package.
Exit 0 = pass; exit 1 with one FAIL line per violated check.

Checks:
- P0.a manifest present with the nine schema fields.
- P0.b every component reference's locator resolves inside the package.
- P0.c qualification entries are verdict-contract complete.
- P0.d the package's own runner+scoring discriminates over the case's
  evidence/inner-impls/ pool (interpreter supplied from case evidence).
- wf.1 the package oracle rejects a transcript whose stages run out of
  order.
- wf.2 the package oracle rejects a join whose consumed identity
  differs from the frozen upstream identity.
- wf.3 gate coverage is per-edge: the last-edge-ungated inner
  near-miss is failed.
- wf.4 build ordering: the provenance event ledger records the
  components frozen before the qualification recorded against them,
  and every qualification verdict's covers resolve to components of
  this package.
- wf.5 design-evidence flow direction: the design component's
  evidence-source lines never point at the package's own downstream
  components (cases/, runner/, scoring/, qualification/).
- wf.6 the package-level aggregate gate rejects an empty run.

Scratch-copy hygiene: the implementation, the interpreter, and the
inner pool are copied to a temporary directory before any execution;
nothing under the case directory is written.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MANIFEST_FIELDS = frozenset(
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
ENTRY_FIELDS = ("criterion", "verdict", "oracle", "oracle_class", "evidence", "covers", "required")
VERDICTS = ("PASS", "FAIL", "UNVERIFIED")
ORACLE_CLASSES = ("deterministic", "judged", "evidence")
DOWNSTREAM_PREFIXES = ("cases/", "runner/", "scoring/", "qualification/")
DOWNSTREAM_NAMES = ("cases", "runner", "scoring", "qualification")
SUBPROC_TIMEOUT = 240


# ---- P0.e: the post-qualification manifest fields -------------------
# `compositions/references/benchmaker-manifest.md` owns the eight. None is
# re-derivable after the fact, so a package that omits one cannot be repaired
# by a consumer. This case covers `retirement_trigger`:
# this case is about records landing in the right place in the right order,
# and a firing recorded in the manifest is the wrong place.
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
PROBED_MANIFEST_FIELDS = {"retirement_trigger": "constrained"}
REQUIRED_MANIFEST_FIELDS = frozenset(MANIFEST_FIELDS)
ALLOWED_MANIFEST_FIELDS = REQUIRED_MANIFEST_FIELDS | POST_QUALIFICATION_FIELDS

_FIRING_KEYS = ("fired", "fired_at", "firing", "retired_at")
_FIRING_MARKS = ("fired on", "fired at", "has fired", "trigger fired")


def _retirement_trigger_failures(manifest, out):
    trigger = manifest.get("retirement_trigger")
    if isinstance(trigger, dict):
        for key in sorted(trigger):
            if key.lower() in _FIRING_KEYS:
                out.append("retirement_trigger records a firing ('%s'); the manifest carries "
                           "the declaration only" % key)
        trigger = trigger.get("declaration")
    if not (isinstance(trigger, str) and trigger.strip()):
        out.append("retirement_trigger states no declaration")
        return
    lowered = trigger.lower()
    for mark in _FIRING_MARKS:
        if mark in lowered:
            out.append("retirement_trigger records a firing; a firing belongs in the "
                       "measurement record outside the package")
            break


def post_qualification_failures(manifest):
    """P0.e — the field(s) this case covers, against the manifest contract."""
    if not isinstance(manifest, dict):
        return ["manifest is not a JSON object"]
    out = []
    _retirement_trigger_failures(manifest, out)
    return out


def resolve_locator(pkg, locator):
    if not isinstance(locator, str) or not locator or "\\" in locator:
        return None
    if locator.startswith("/") or (len(locator) > 1 and locator[1] == ":"):
        return None
    resolved = os.path.normpath(os.path.join(str(pkg), locator))
    root = os.path.normpath(str(pkg))
    if not (resolved == root or resolved.startswith(root + os.sep)):
        return None
    return Path(resolved)


def child_env():
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_python(args, cwd):
    return subprocess.run(
        [sys.executable] + [str(a) for a in args],
        cwd=str(cwd),
        env=child_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=SUBPROC_TIMEOUT,
    )


def check_p0a(pkg, errors):
    manifest_path = pkg / "manifest.json"
    if not manifest_path.is_file():
        errors.append("P0.a: no manifest.json at the package root")
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except ValueError as error:
        errors.append("P0.a: manifest.json is not valid JSON: {}".format(error))
        return None
    fields = set(manifest)
    for missing in sorted(MANIFEST_FIELDS - fields):
        errors.append("P0.a: manifest is missing field '{}'".format(missing))
    for extra in sorted(fields - ALLOWED_MANIFEST_FIELDS):
        errors.append("P0.a: manifest carries field '{}' outside the schema".format(extra))
    for message in post_qualification_failures(manifest):
        errors.append("P0.e: " + message)
    return manifest


def check_p0b(pkg, manifest, errors):
    for name in COMPONENT_FIELDS:
        ref = manifest.get(name)
        if not isinstance(ref, dict) or "locator" not in ref:
            errors.append("P0.b: component '{}' is not a locator reference".format(name))
            continue
        resolved = resolve_locator(pkg, ref["locator"])
        if resolved is None or not resolved.exists():
            errors.append("P0.b: component '{}' locator '{}' does not resolve inside the package".format(name, ref["locator"]))


def load_qualification(pkg, manifest, errors):
    ref = manifest.get("qualification")
    if not isinstance(ref, dict):
        return None
    resolved = resolve_locator(pkg, ref.get("locator", ""))
    if resolved is None:
        return None
    qual_path = resolved / "qualification.json" if resolved.is_dir() else resolved
    if not qual_path.is_file():
        errors.append("P0.c: no qualification.json under '{}'".format(ref.get("locator")))
        return None
    try:
        qual = json.loads(qual_path.read_text(encoding="utf-8"))
    except ValueError as error:
        errors.append("P0.c: qualification.json is not valid JSON: {}".format(error))
        return None
    if not isinstance(qual, dict):
        errors.append("P0.c: qualification.json is not a JSON object")
        return None
    return qual


def check_p0c(qual, errors):
    if qual is None:
        return
    if "gaps" not in qual or not isinstance(qual["gaps"], list):
        errors.append("P0.c: qualification 'gaps' field must be an explicit list ([] allowed)")
    overall = qual.get("overall")
    if overall not in VERDICTS:
        errors.append("P0.c: qualification 'overall' must be one of {}".format(list(VERDICTS)))
    entries = qual.get("entries")
    if not isinstance(entries, list) or not entries:
        errors.append("P0.c: qualification carries no entries")
        return
    required_fail = False
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append("P0.c: entry {} is not an object".format(index))
            continue
        for field in ENTRY_FIELDS:
            if field not in entry:
                errors.append("P0.c: entry {} is missing '{}'".format(index, field))
        if entry.get("verdict") not in VERDICTS:
            errors.append("P0.c: entry {} verdict must be one of {}".format(index, list(VERDICTS)))
        if entry.get("oracle_class") not in ORACLE_CLASSES:
            errors.append("P0.c: entry {} oracle_class must be one of {}".format(index, list(ORACLE_CLASSES)))
        if not isinstance(entry.get("required"), bool):
            errors.append("P0.c: entry {} 'required' must be a boolean".format(index))
        evidence = entry.get("evidence")
        if entry.get("verdict") == "PASS" and not (isinstance(evidence, str) and evidence.strip()):
            errors.append("P0.c: entry {} is PASS with an empty evidence field".format(index))
        if entry.get("verdict") == "FAIL" and entry.get("required") is True:
            required_fail = True
    if overall == "PASS" and required_fail:
        errors.append("P0.c: overall PASS coexists with a required FAIL")


def impl_expectation(name):
    if name == "reference" or name.startswith("good"):
        return "pass"
    return "fail"


def run_package(pkg, impl_dir, interpreter, work):
    return run_python(
        [pkg / "runner" / "run.py", impl_dir, "--interpreter", interpreter],
        cwd=work,
    )


def check_p0d(pkg, pool, interpreter, work, errors):
    impls = sorted(p for p in pool.iterdir() if p.is_dir())
    if not impls:
        errors.append("P0.d: inner pool is empty")
        return
    for impl in impls:
        proc = run_package(pkg, impl, interpreter, work)
        expected = impl_expectation(impl.name)
        if expected == "pass" and proc.returncode != 0:
            errors.append("P0.d: inner impl '{}' must pass but the package failed it".format(impl.name))
        if expected == "fail" and proc.returncode == 0:
            errors.append("P0.d: inner impl '{}' must fail but the package passed it".format(impl.name))


def reference_transcript(interpreter, pool, work, errors):
    pipeline = pool / "reference" / "pipeline.json"
    proc = run_python([interpreter, pipeline], cwd=work)
    if proc.returncode != 0:
        errors.append("wf.1: interpreter failed on the reference pipeline")
        return None
    return proc.stdout.decode("utf-8", "replace").splitlines()


def stage_blocks(lines):
    blocks, current, name = [], [], None
    for line in lines:
        parts = line.split()
        if parts and parts[0] == "STAGE-START":
            name, current = parts[1], [line]
        elif parts and parts[0] == "STAGE-END":
            current.append(line)
            blocks.append((name, current))
            current, name = [], None
        elif name is not None:
            current.append(line)
    return blocks


def check_oracle_rejects(pkg, work, label, lines, errors, message):
    transcript = work / (label + ".txt")
    transcript.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    proc = run_python([pkg / "runner" / "check_transcript.py", transcript], cwd=work)
    if proc.returncode == 0:
        errors.append(message)


def check_wf1_wf2_wf6(pkg, interpreter, pool, work, errors):
    lines = reference_transcript(interpreter, pool, work, errors)
    if lines is None:
        return
    blocks = dict((name, block) for name, block in stage_blocks(lines))
    if not all(stage in blocks for stage in ("spec", "build", "verify")):
        errors.append("wf.1: reference transcript is missing canonical stages")
        return
    out_of_order = blocks["spec"] + blocks["verify"] + blocks["build"]
    check_oracle_rejects(
        pkg, work, "wf1-out-of-order", out_of_order, errors,
        "wf.1: package oracle accepts a transcript whose stages run out of order",
    )
    tampered = []
    tampered_done = False
    for line in lines:
        parts = line.split()
        if not tampered_done and len(parts) == 5 and parts[0] == "JOIN" and parts[4] != "MISSING":
            parts[4] = "0" * 64
            tampered.append(" ".join(parts))
            tampered_done = True
        else:
            tampered.append(line)
    if not tampered_done:
        errors.append("wf.2: reference transcript carries no join to tamper")
    else:
        check_oracle_rejects(
            pkg, work, "wf2-join-mismatch", tampered, errors,
            "wf.2: package oracle accepts a join whose identity differs from the frozen record",
        )
    check_oracle_rejects(
        pkg, work, "wf6-empty", [], errors,
        "wf.6: package-level aggregate gate accepts an empty run",
    )


def check_wf3(pkg, pool, interpreter, work, errors):
    near_miss = pool / "near-miss-lastgate"
    if not near_miss.is_dir():
        errors.append("wf.3: inner pool has no near-miss-lastgate")
        return
    proc = run_package(pkg, near_miss, interpreter, work)
    if proc.returncode == 0:
        errors.append("wf.3: the last-edge-ungated inner near-miss passes; gate coverage is not per-edge")


def check_wf4(pkg, manifest, qual, errors):
    events_path = pkg / "provenance" / "events.md"
    if not events_path.is_file():
        errors.append("wf.4: no provenance/events.md event ledger")
    else:
        order = {}
        for index, line in enumerate(events_path.read_text(encoding="utf-8", errors="replace").splitlines()):
            for token in ("components-frozen", "qualification-recorded"):
                if token in line and token not in order:
                    order[token] = index
        missing = [t for t in ("components-frozen", "qualification-recorded") if t not in order]
        if missing:
            errors.append("wf.4: event ledger is missing events: {}".format(", ".join(missing)))
        elif not (order["components-frozen"] < order["qualification-recorded"]):
            errors.append("wf.4: event ledger records qualification before its components were frozen (late operation)")
    if qual is None or manifest is None:
        return
    component_locators = set()
    for name in COMPONENT_FIELDS:
        ref = manifest.get(name)
        if isinstance(ref, dict) and isinstance(ref.get("locator"), str):
            component_locators.add(ref["locator"])
    for index, entry in enumerate(qual.get("entries", []) or []):
        if not isinstance(entry, dict):
            errors.append("wf.4: qualification entry {} is not an object".format(index))
            continue
        covers = entry.get("covers")
        if not isinstance(covers, dict):
            continue
        for value in covers.values():
            if value not in component_locators:
                errors.append("wf.4: qualification entry {} covers something that is no component of this package".format(index))


def check_wf5(pkg, errors):
    design_path = pkg / "provenance" / "evaluation-design.md"
    if not design_path.is_file():
        errors.append("wf.5: no provenance/evaluation-design.md")
        return
    sources = []
    for line in design_path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("evidence-source:"):
            sources.append(stripped.split(":", 1)[1].strip())
    if not sources:
        errors.append("wf.5: design component names no evidence-source")
        return
    for source in sources:
        normalized = source.lower()
        if normalized.startswith(DOWNSTREAM_PREFIXES) or normalized in DOWNSTREAM_NAMES:
            errors.append(
                "wf.5: design cites downstream component '{}' as its own evidence source (reverse flow)".format(source)
            )


def main(argv):
    if len(argv) != 2:
        print("FAIL: usage: check.py <impl-dir>")
        return 1
    case_dir = Path(os.environ.get("CASE_DIR") or os.getcwd()).resolve()
    impl_src = Path(argv[1])
    if not impl_src.is_absolute():
        impl_src = (case_dir / impl_src).resolve()
    errors = []
    if not impl_src.is_dir():
        print("FAIL: implementation directory '{}' does not exist".format(argv[1]))
        return 1
    tmp = Path(tempfile.mkdtemp(prefix="cs-workflow-probe-"))
    try:
        pkg = tmp / "pkg"
        shutil.copytree(str(impl_src), str(pkg))
        pool = tmp / "inner-impls"
        shutil.copytree(str(case_dir / "evidence" / "inner-impls"), str(pool))
        interpreter = tmp / "interpreter.py"
        shutil.copyfile(str(case_dir / "evidence" / "interpreter.py"), str(interpreter))
        work = tmp / "work"
        work.mkdir()

        manifest = check_p0a(pkg, errors)
        qual = None
        if manifest is not None and not (MANIFEST_FIELDS - set(manifest)):
            check_p0b(pkg, manifest, errors)
            qual = load_qualification(pkg, manifest, errors)
            check_p0c(qual, errors)
        check_p0d(pkg, pool, interpreter, work, errors)
        check_wf1_wf2_wf6(pkg, interpreter, pool, work, errors)
        check_wf3(pkg, pool, interpreter, work, errors)
        check_wf4(pkg, manifest, qual, errors)
        check_wf5(pkg, errors)
    except subprocess.TimeoutExpired:
        errors.append("a package execution exceeded {} s".format(SUBPROC_TIMEOUT))
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)
    for line in errors:
        print("FAIL: " + line)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
