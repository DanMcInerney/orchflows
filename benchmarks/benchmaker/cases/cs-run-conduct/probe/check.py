#!/usr/bin/env python3
"""Case probe for cs-run-conduct. The case author's sanity oracle.

Deterministic audit of a benchmaker RUN RECORD plus its minimal package,
against the grammar fixed in evidence/record-schema.md. This manifest-facing
CLI checks P0.a–P0.c, P0.e, and rc.1 locally; ``record_checks`` owns rc.2–rc.8.

Usage: check.py [IMPL_DIR]. CASE_IMPL outranks the positional. The
implementation is copied to a scratch directory before inspection; nothing
under the case directory is ever written. Exit 0 when every check passes, else
exit 1 with one FAIL line per finding.

Stdlib only. Python 3.9+.
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

import record_checks


CASE_ROOT = Path(__file__).resolve().parent.parent
STAGES = ("acquire", "design", "materialize", "qualify", "manifest")
MANIFEST_FIELDS = (
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
COMPONENTS = (
    "evaluation_design",
    "runnable_cases",
    "runner",
    "scoring",
    "provenance",
    "qualification",
)
ENTRY_FIELDS = ("verdict", "oracle", "oracle_class", "evidence", "covers", "required")
VERDICTS = ("PASS", "FAIL", "UNVERIFIED")


# ---- P0.e: the post-qualification manifest fields -------------------
# `compositions/references/benchmaker-manifest.md` owns the eight. None is
# re-derivable after the fact, so a package that omits one cannot be repaired
# by a consumer. This case covers `builders`: run conduct is the record of who
# ran what; the builder context is the part a later revision cannot recover.
# `tools/validate_cases.py` reads this literal assignment.
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
PROBED_MANIFEST_FIELDS = {"builders": "constrained"}
REQUIRED_MANIFEST_FIELDS = frozenset(MANIFEST_FIELDS)
ALLOWED_MANIFEST_FIELDS = REQUIRED_MANIFEST_FIELDS | POST_QUALIFICATION_FIELDS

_BUILDER_KEYS = ("model_id", "effort", "host_binding")


def _builder_failures(manifest, out):
    builders = manifest.get("builders")
    if not isinstance(builders, dict) or not builders:
        out.append("'builders' must record the builder context of each case")
        return
    for case_id in sorted(builders):
        record = builders[case_id]
        if not isinstance(record, dict):
            out.append("builders['%s'] is not a builder-context record" % case_id)
            continue
        absent = [key for key in _BUILDER_KEYS if key not in record]
        if absent:
            out.append("builders['%s'] does not record %s" % (case_id, ", ".join(absent)))
        unrecorded = [key for key in _BUILDER_KEYS if record.get(key) is None]
        if unrecorded and not str(record.get("note") or "").strip():
            out.append(
                "builders['%s'] leaves %s null with no note saying why"
                % (case_id, ", ".join(unrecorded))
            )


def post_qualification_failures(manifest):
    """P0.e — the field(s) this case covers, against the manifest contract."""

    if not isinstance(manifest, dict):
        return ["manifest is not a JSON object"]
    out = []
    _builder_failures(manifest, out)
    return out


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
    return path.read_text(encoding="utf-8", errors="replace")


def lines_of(path):
    return read(path).splitlines()


def parts_of(line):
    fields = {}
    for segment in line.split("|"):
        if ":" in segment:
            key, value = segment.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


def check_package(impl, failures):
    pkg = impl / "package"
    manifest_path = pkg / "manifest.json"
    if not manifest_path.is_file():
        failures.append("P0.a: no package/manifest.json")
        return None
    try:
        manifest = json.loads(read(manifest_path))
    except ValueError as error:
        failures.append("P0.a: manifest.json does not parse: %s" % error)
        return None
    for field in MANIFEST_FIELDS:
        if field not in manifest:
            failures.append("P0.a: manifest is missing field '%s'" % field)
    if not all(field in manifest for field in MANIFEST_FIELDS):
        return manifest
    for message in post_qualification_failures(manifest):
        failures.append("P0.e: " + message)
    for name in COMPONENTS:
        ref = manifest[name]
        if not (isinstance(ref, dict) and isinstance(ref.get("locator"), str)):
            failures.append("P0.b: component '%s' is not a locator reference" % name)
            continue
        resolved = (pkg / ref["locator"]).resolve()
        if not resolved.is_file():
            failures.append(
                "P0.b: component '%s' locator '%s' resolves to no file"
                % (name, ref["locator"])
            )
    if not isinstance(manifest["gaps"], list):
        failures.append("P0.a: manifest gaps must be an explicit list")
    qual_ref = manifest.get("qualification")
    if isinstance(qual_ref, dict) and isinstance(qual_ref.get("locator"), str):
        qual_path = (pkg / qual_ref["locator"]).resolve()
        if qual_path.is_file():
            check_qualification(qual_path, failures)
    return manifest


def check_qualification(path, failures):
    try:
        record = json.loads(read(path))
    except ValueError as error:
        failures.append("P0.c: qualification component does not parse: %s" % error)
        return
    entries = record.get("entries")
    if not isinstance(entries, list) or not entries:
        failures.append("P0.c: qualification carries no entries list")
        return
    overall = record.get("overall")
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
    if overall == "PASS" and required_fail:
        failures.append("P0.c: overall PASS coexists with a required FAIL")


def check_stages(impl, record, failures):
    stages_path = record / "stages.md"
    if not stages_path.is_file():
        failures.append("rc.1: no record/stages.md")
        return
    slines = lines_of(stages_path)
    seen_stages = {}
    for line in slines:
        stripped = line.strip()
        if stripped.startswith("stage:"):
            fields = parts_of(stripped)
            name = fields.get("stage", "")
            if name not in STAGES:
                failures.append("rc.1: stage line names unknown stage '%s'" % name)
                continue
            if name in seen_stages:
                failures.append("rc.1: stage '%s' declared twice" % name)
            seen_stages[name] = fields.get("allocation", "")
    for name in STAGES:
        if name not in seen_stages:
            failures.append("rc.1: no allocation line for stage '%s'" % name)
        elif not seen_stages[name].strip():
            failures.append("rc.1: stage '%s' has an empty allocation" % name)
    claimed = {}
    for line in slines:
        stripped = line.strip()
        if not stripped.startswith("item:"):
            continue
        fields = parts_of(stripped)
        item_id = fields.get("item", "?")
        stage = fields.get("stage", "")
        artifact = fields.get("artifact", "")
        if stage not in STAGES:
            failures.append(
                "rc.1: item '%s' names stage '%s', not one of the five" % (item_id, stage)
            )
        if not artifact:
            failures.append("rc.1: item '%s' claims no artifact" % item_id)
            continue
        if artifact in claimed:
            failures.append("rc.1: artifact '%s' is claimed by two items" % artifact)
        claimed[artifact] = item_id
        if not (impl / artifact).is_file():
            failures.append("rc.1: item '%s' claims missing artifact '%s'" % (item_id, artifact))
    inventory = set()
    for top in ("record", "package"):
        base = impl / top
        if base.is_dir():
            for path in sorted(base.rglob("*")):
                if path.is_file():
                    inventory.add(path.relative_to(impl).as_posix())
    inventory.discard("record/stages.md")
    for orphan in sorted(inventory - set(claimed)):
        failures.append("rc.1: artifact '%s' exists but no stage claims it" % orphan)


def audit(impl):
    failures = []
    record = impl / "record"
    if not record.is_dir():
        failures.append("rc.1: no record/ tree in the returned artifacts")
    manifest = check_package(impl, failures)
    if record.is_dir():
        check_stages(impl, record, failures)
        record_checks.check_record(impl, record, manifest, failures)
    return failures


def main(argv):
    if len(argv) > 2:
        emit("usage: check.py [IMPL_DIR]")
        return 2
    source = resolve(argv[1] if len(argv) == 2 else None)
    if not source.is_dir():
        emit("no such implementation directory: %s" % source)
        return 2
    scratch = tempfile.mkdtemp(prefix="cs-run-conduct-")
    try:
        impl = Path(scratch) / "impl"
        shutil.copytree(str(source), str(impl))
        failures = audit(impl)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    for failure in failures:
        emit(failure)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
