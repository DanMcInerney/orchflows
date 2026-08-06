#!/usr/bin/env python3
"""Case probe for multi-domain: the case author's sanity oracle, NOT the benchmark.

The probe is declared only in `case.toml` (`probe`); nothing under `evidence/`
references it, so a benchmark builder never reads it.

usage: python probe.py [<target>]

<target> is a path to the tool under probe: either the reference
`target/scaffold.py`, a seed directory, or a seed's `scaffold.py`. With no
argument (or the literal, unsubstituted `{target}`) the probe falls back to
`$CASE_TARGET` and then to this case's reference target, so a runner that
executes the probe string verbatim still checks the reference.

Exit 0 when every check passes; exit 1 with named failures otherwise.

The probe checks BOTH halves of the generator's output:
  code half   deterministic  generated validator run against a record matrix
  report half structural     report's field table and message list checked
                             against the schema and against the message set
                             the generated validator actually emits
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET_BASENAME = "scaffold.py"

SCHEMA = {
    "record": "Contact",
    "fields": [
        {"name": "email", "type": "str", "required": True, "max_len": 64},
        {"name": "age", "type": "int", "required": False},
        {"name": "nickname", "type": "str", "required": False, "max_len": 16},
    ],
}

VALID_RECORD = {"email": "ada@example.com", "age": 36, "nickname": "ada"}

# (label, record, expected error list) -- the code half, checked exactly.
CODE_MATRIX = [
    ("valid record", VALID_RECORD, []),
    ("missing required field", {"age": 36}, ["email: required"]),
    ("required field wrong type", dict(VALID_RECORD, email=7), ["email: expected str"]),
    ("required field too long", dict(VALID_RECORD, email="a" * 65), ["email: max length 64"]),
    ("optional field wrong type", dict(VALID_RECORD, age="thirty"), ["age: expected int"]),
    ("optional field too long", dict(VALID_RECORD, nickname="n" * 17), ["nickname: max length 16"]),
    ("bool is not an int", dict(VALID_RECORD, age=True), ["age: expected int"]),
    ("empty record", {}, ["email: required"]),
    # Two independent violations: every one must be reported, in field order.
    ("two violations", {"age": "thirty"}, ["email: required", "age: expected int"]),
]

# The field table the report must carry, restated independently of the target.
EXPECTED_ROWS = [
    ("email", "str", "required", "max length 64"),
    ("age", "int", "optional", "none"),
    ("nickname", "str", "optional", "max length 16"),
]


def resolve_target(argv):
    """Resolve the tool under probe from argv, $CASE_TARGET, or the reference."""
    here = Path(__file__).resolve().parent
    raw = argv[1].strip() if len(argv) > 1 else ""
    if raw in ("", "{target}"):
        raw = os.environ.get("CASE_TARGET", "").strip()
    if raw in ("", "{target}"):
        return here / "target" / TARGET_BASENAME
    given = Path(raw)
    tries = [given] if given.is_absolute() else [Path.cwd() / given, here / given]
    for candidate in tries:
        if candidate.is_dir():
            candidate = candidate / TARGET_BASENAME
        if candidate.is_file():
            return candidate.resolve()
    raise SystemExit("probe: cannot resolve target from %r" % raw)


def load_generated(path):
    """Import the generated validator module from its file."""
    spec = importlib.util.spec_from_file_location("generated_validator_probe", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def single_violation_records():
    """One record per possible violation, each carrying exactly one defect."""
    out = []
    for field in SCHEMA["fields"]:
        name = field["name"]
        if field["required"]:
            record = dict(VALID_RECORD)
            record.pop(name, None)
            out.append(record)
        wrong = "not-a-number" if field["type"] == "int" else 7
        out.append(dict(VALID_RECORD, **{name: wrong}))
        if field["type"] == "str" and field.get("max_len") is not None:
            out.append(dict(VALID_RECORD, **{name: "x" * (field["max_len"] + 1)}))
    return out


def section_lines(text, heading):
    """The lines of one `## heading` section, up to the next heading."""
    lines = text.splitlines()
    out = []
    inside = False
    for line in lines:
        if line.startswith("## "):
            if inside:
                break
            inside = line.strip() == heading
            continue
        if inside:
            out.append(line)
    return out


def check_report(report_text, observed_messages, fail):
    """The report half: field table and message list, checked structurally."""
    heads = [line for line in report_text.splitlines() if line.startswith("# ")]
    if not heads or SCHEMA["record"] not in heads[0]:
        fail("report title does not name the %s record: %r" % (SCHEMA["record"], heads[:1]))

    rows = []
    for line in section_lines(report_text, "## Fields"):
        if not line.strip().startswith("|"):
            continue
        cells = tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
        if cells[0] in ("field", "---"):
            continue
        rows.append(cells)
    if rows != EXPECTED_ROWS:
        fail("report field table disagrees with the schema:\n    got      %r\n    expected %r" % (rows, EXPECTED_ROWS))

    listed = []
    for line in section_lines(report_text, "## Error messages"):
        stripped = line.strip()
        if stripped.startswith("- `") and stripped.endswith("`"):
            listed.append(stripped[3:-1])
    if set(listed) != observed_messages:
        missing = sorted(observed_messages - set(listed))
        invented = sorted(set(listed) - observed_messages)
        fail(
            "report message list disagrees with the generated validator:\n"
            "    not listed by the report: %r\n"
            "    listed but never emitted: %r" % (missing, invented)
        )
    if len(listed) != len(set(listed)):
        fail("report message list repeats an entry: %r" % (listed,))


def run(target):
    failures = []

    def fail(message):
        failures.append(message)

    work = Path(tempfile.mkdtemp(prefix="multi-domain-probe-"))
    try:
        schema_path = work / "contacts.json"
        schema_path.write_text(json.dumps(SCHEMA, indent=2), encoding="utf-8")
        outdir = work / "out"
        result = subprocess.run(
            [sys.executable, str(target), str(schema_path), str(outdir)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            fail("generator exited %d: %s" % (result.returncode, result.stderr.strip()))
            return failures

        module_path = outdir / "validate_contact.py"
        report_path = outdir / "REPORT.md"
        if not module_path.is_file():
            fail("generator emitted no code artifact at %s" % module_path.name)
        if not report_path.is_file():
            fail("generator emitted no report artifact at REPORT.md")
        if failures:
            return failures

        try:
            module = load_generated(module_path)
        except Exception as exc:  # noqa: BLE001 - any import failure is a probe failure
            fail("generated validator does not import: %s: %s" % (type(exc).__name__, exc))
            return failures
        if not hasattr(module, "validate"):
            fail("generated validator exposes no validate()")
            return failures

        for label, record, expected in CODE_MATRIX:
            try:
                got = module.validate(dict(record))
            except Exception as exc:  # noqa: BLE001
                fail("code half %r raised %s: %s" % (label, type(exc).__name__, exc))
                continue
            if list(got) != expected:
                fail("code half %r: got %r, expected %r" % (label, got, expected))

        observed = set()
        for record in single_violation_records():
            try:
                observed.update(module.validate(dict(record)))
            except Exception as exc:  # noqa: BLE001
                fail("message survey raised %s: %s" % (type(exc).__name__, exc))
        check_report(report_path.read_text(encoding="utf-8"), observed, fail)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return failures


def main(argv):
    target = resolve_target(argv)
    failures = run(target)
    if failures:
        sys.stderr.write("probe FAIL (%s)\n" % target)
        for failure in failures:
            sys.stderr.write("  - %s\n" % failure)
        return 1
    sys.stdout.write("probe PASS (%s)\n" % target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
