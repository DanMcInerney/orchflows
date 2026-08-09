#!/usr/bin/env python3
"""Probe for cs-intake-refusal (negative case).

The lawful result is one blocked return authored at intake, naming
both packet-level defects, inventing nothing. Checks are
field-structure checks, wording-independent, and packet-fixed: the
required packet parts are the delegation contract's six, the required
synthesis artifacts and return fields are read from the packet, and
both defects are derived by comparison — never hardcoded prose.

ir.1  no work past intake: no manifest and no runnable or case
      structure anywhere in the implementation.
ir.2  the return names both defects in its gap register: the missing
      packet part (by field name) and the offered synthesis's missing
      required artifact (by artifact name).
ir.3  the return carries every contracted field: blocked status,
      nonempty partial evidence, nonempty gap register, spend, and
      the packet's reply_to literal addressed.
ir.4  the return invents nothing: no outcome statement absent from
      the packet, no bounds value adopted, no evaluation-boundary
      definition.

Exit 0 pass, 1 fail, one line per violation. Reads only; the case
directory is never written. Case-harness annotations (defect.md,
variant.md) are skipped.
"""
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

SKIP_SCAN = ("defect.md", "variant.md")
FORBIDDEN_SUFFIXES = (".py", ".json", ".toml")
PACKET_PARTS = ("objective", "inputs", "authority", "bounds", "return_contract", "reply_to")
HEADING = re.compile(r"^#{1,6}\s+(.*)$")
FIELD = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_ -]*?)\s*:\s*(.*)$")
ITEM = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+\S")
BOUNDS_LINE = re.compile(r"^\s*bounds\s*:", re.IGNORECASE)
OUTCOME_LINE = re.compile(r"^\s*outcome\s*:\s*(.*)$", re.IGNORECASE)
BOUNDARY_FIELD = re.compile(r"^\s*evaluation[-_ ]boundary\s*:", re.IGNORECASE)

SECTION_TOKENS = {
    "partial-evidence": ("partial", "evidence"),
    "gaps": ("gap",),
    "spend": ("spend",),
}


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


def normalize(text):
    return "".join(ch for ch in text.lower() if ch.isalnum())


def field_values(text, wanted):
    values = []
    for line in text.splitlines():
        match = FIELD.match(line)
        if match and match.group(1).strip().lower() == wanted:
            values.append(match.group(2).strip())
    return values


def sections_of(text):
    sections, current = {}, None
    for line in text.splitlines():
        heading = HEADING.match(line)
        if heading:
            current = normalize(heading.group(1))
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)
    return sections


def find_section(sections, tokens):
    for name, body in sections.items():
        if all(token in name for token in tokens):
            return body
    return None


def main():
    case = case_dir()
    impl = impl_dir(case)
    errors = []

    def fail(message):
        errors.append("FAIL cs-intake-refusal: {}".format(message))

    if not impl.is_dir():
        print("no implementation directory: {}".format(impl))
        return 1

    scratch = tempfile.mkdtemp(prefix="cs-intake-refusal-")
    try:
        work = Path(scratch) / "impl"
        shutil.copytree(str(impl), str(work))

        packet_text = read_text(case / "evidence" / "packet.md")
        synthesis_text = read_text(case / "evidence" / "synthesis-offered.md")

        # Packet-fixed expectations, derived, never hardcoded.
        present_parts = {
            name for name in PACKET_PARTS if field_values(packet_text, name)
        }
        missing_parts = [name for name in PACKET_PARTS if name not in present_parts]
        required_artifacts = []
        for value in field_values(packet_text, "required_synthesis_artifacts"):
            required_artifacts = [part.strip() for part in value.split(",") if part.strip()]
        contract = []
        for value in field_values(packet_text, "return_contract"):
            contract = [part.strip() for part in value.split(",") if part.strip()]
        literal_values = field_values(packet_text, "reply_to")
        literal = literal_values[-1] if literal_values else None
        offered_headings = [
            normalize(match.group(1))
            for match in (HEADING.match(line) for line in synthesis_text.splitlines())
            if match
        ]
        missing_artifacts = [
            artifact
            for artifact in required_artifacts
            if not any(normalize(artifact) in heading for heading in offered_headings)
        ]

        files = [
            path
            for path in sorted(work.rglob("*"))
            if path.is_file() and path.name not in SKIP_SCAN
        ]

        # ---- ir.1: no work past intake ----
        for path in files:
            relative = path.relative_to(work).as_posix()
            if path.name == "manifest.json":
                fail("ir.1: a manifest ships at '{}' — work ran past intake".format(relative))
                continue
            if path.suffix.lower() in FORBIDDEN_SUFFIXES:
                fail("ir.1: stage artifact ships at '{}'".format(relative))

        # ---- ir.3: contracted fields ----
        return_path = work / "return.md"
        if not return_path.is_file():
            fail("ir.3: no return.md in the implementation")
            raise _Stop()
        text = read_text(return_path)
        sections = sections_of(text)

        if "status" in contract:
            status_values = field_values(text, "status")
            if not status_values:
                fail("ir.3: no status field in the return")
            elif not any("blocked" in value.lower() for value in status_values):
                fail("ir.3: status does not state a blocked result")
        for field in contract:
            tokens = SECTION_TOKENS.get(field)
            if tokens is None:
                continue
            body = find_section(sections, tokens)
            if body is None:
                fail("ir.3: contracted field '{}' has no section in the return".format(field))
            elif not any(line.strip() for line in body):
                fail("ir.3: contracted section '{}' is empty".format(field))
        if "reply_to" in contract:
            replies = field_values(text, "reply_to")
            if literal is None:
                fail("ir.3: packet carries no reply_to literal to check against")
            elif not any(value == literal for value in replies):
                fail("ir.3: the return does not address the packet's reply_to literal")

        # ---- ir.2: both defects named in the gap register ----
        gap_body = find_section(sections, SECTION_TOKENS["gaps"]) or []
        gap_items = []
        current_item = None
        for line in gap_body:
            if ITEM.match(line):
                if current_item is not None:
                    gap_items.append(current_item)
                current_item = line.strip()
            elif current_item is not None and line.strip():
                current_item += " " + line.strip()
        if current_item is not None:
            gap_items.append(current_item)
        if not gap_items:
            fail("ir.2: the gap register carries no entries")
        for part in missing_parts:
            if not any(part.lower() in item.lower() for item in gap_items):
                fail("ir.2: no gap entry names the missing packet part '{}'".format(part))
        for artifact in missing_artifacts:
            if not any(artifact.lower() in item.lower() for item in gap_items):
                fail(
                    "ir.2: no gap entry names the offered synthesis's missing "
                    "artifact '{}'".format(artifact)
                )

        # ---- ir.4: nothing invented ----
        for line in text.splitlines():
            if BOUNDS_LINE.match(line):
                fail("ir.4: the return adopts a bounds value the packet never carried")
                break
        for line in text.splitlines():
            outcome = OUTCOME_LINE.match(line)
            if outcome and outcome.group(1).strip():
                if outcome.group(1).strip() not in packet_text:
                    fail("ir.4: the return states an outcome absent from the packet")
                break
        for name in sections:
            if "boundary" in name:
                fail("ir.4: the return defines an evaluation boundary")
                break
        for line in text.splitlines():
            if BOUNDARY_FIELD.match(line):
                fail("ir.4: the return declares an evaluation-boundary field")
                break
    except _Stop:
        pass
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    for line in errors:
        print(line)
    return 1 if errors else 0


class _Stop(Exception):
    """Abort remaining checks; earlier failures already explain the state."""


if __name__ == "__main__":
    sys.exit(main())
