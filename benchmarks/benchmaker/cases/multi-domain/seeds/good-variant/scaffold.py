#!/usr/bin/env python3
"""Scaffold a record validator and its report from one schema (variant).

A second good seed: same observable behaviour as the reference, different
internal structure and different report prose. A benchmark that matches the
reference's source text or the report's wording rather than its meaning fails
this seed, and failing a good seed is a benchmark defect.

usage: python scaffold.py <schema.json> <outdir>
"""

import json
import sys
from pathlib import Path

TYPE_TESTS = {
    "int": "not isinstance(value, int) or isinstance(value, bool)",
    "str": "not isinstance(value, str)",
}


def limit_of(field):
    return field.get("max_len") if field["type"] == "str" else None


def error_strings(field):
    name, kind = field["name"], field["type"]
    messages = ["{}: required".format(name)] if field["required"] else []
    messages.append("{}: expected {}".format(name, kind))
    limit = limit_of(field)
    if limit is not None:
        messages.append("{}: max length {}".format(name, limit))
    return messages


def _checks(field, indent):
    """The type check and optional length check, at one indent level."""
    pad = " " * indent
    name, limit = field["name"], limit_of(field)
    out = [
        "{}if {}:".format(pad, TYPE_TESTS[field["type"]]),
        "{}    errors.append({!r})".format(pad, "{}: expected {}".format(name, field["type"])),
    ]
    if limit is not None:
        out.append("{}elif len(value) > {}:".format(pad, limit))
        out.append("{}    errors.append({!r})".format(pad, "{}: max length {}".format(name, limit)))
    return out


def _field_block(field):
    name = field["name"]
    head = ["    value = record.get({!r})".format(name)]
    if not field["required"]:
        return head + ["    if value is not None:"] + _checks(field, 8)
    checks = _checks(field, 4)
    # The required branch replaces the leading `if` of the type check chain.
    checks[0] = "    el" + checks[0].strip()
    return head + [
        "    if value is None:",
        "        errors.append({!r})".format("{}: required".format(name)),
    ] + checks


def render_code(schema):
    body = []
    for field in schema["fields"]:
        body.extend(_field_block(field))
    return "\n".join(
        [
            '"""Generated validator for {} records. Do not edit."""'.format(schema["record"]),
            "",
            "",
            "def validate(record):",
            '    """Return every error string for one record, in field order."""',
            "    errors = []",
        ]
        + body
        + ["    return errors", ""]
    )


def render_report(schema, schema_path):
    rows = []
    for field in schema["fields"]:
        limit = limit_of(field)
        rows.append(
            "| {} | {} | {} | {} |".format(
                field["name"],
                field["type"],
                "required" if field["required"] else "optional",
                "none" if limit is None else "max length {}".format(limit),
            )
        )
    bullets = ["- `{}`".format(m) for f in schema["fields"] for m in error_strings(f)]
    return "\n".join(
        [
            "# {} record validation".format(schema["record"]),
            "",
            "This note describes the validator scaffolded from `{}`.".format(Path(schema_path).name),
            "Call `validate(record)`: it hands back one error string per rule the",
            "record breaks, in field order, and an empty list when nothing is wrong.",
            "",
            "## Fields",
            "",
            "| field | type | required | limit |",
            "| --- | --- | --- | --- |",
        ]
        + rows
        + [
            "",
            "## Error messages",
            "",
            "Nothing outside this list is ever emitted.",
            "",
        ]
        + bullets
        + [""]
    )


def main(argv):
    if len(argv) != 3:
        sys.stderr.write("usage: scaffold.py <schema.json> <outdir>\n")
        return 2
    schema_path, outdir = argv[1], argv[2]
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    stem = "validate_" + schema["record"].strip().lower().replace(" ", "_")
    (out / (stem + ".py")).write_text(render_code(schema), encoding="utf-8")
    (out / "REPORT.md").write_text(render_report(schema, schema_path), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
