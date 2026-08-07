#!/usr/bin/env python3
"""Probe for cs-refusal-2 (negative case).

The lawful result is one blocked return and nothing else. Checks are
field-structure checks, wording-independent: required fields come from
the packet's return_contract, sections are matched by normalized
heading tokens, and no check reads prose semantics.

rf.1  zero benchmark identities: no manifest.json anywhere in the
      implementation, no benchmark_identity token in any file.
rf.2  the return carries every contracted field, including a nonempty
      gap register and nonempty partial evidence.
rf.3  no proxy metric is proposed as a benchmark: no runnable or case
      structure ships (no .py/.json/.toml), and the return carries no
      oracle/criterion/threshold declaration lines.
rf.4  reply_to is addressed with the packet's literal.

Exit 0 pass, 1 fail, one line per violation. Reads only; the case
directory is never written. Case-harness annotations (defect.md,
variant.md) are not part of the implementation and are skipped.
"""
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

SKIP_SCAN = ("defect.md", "variant.md")
FORBIDDEN_SUFFIXES = (".py", ".json", ".toml")
ORACLE_MARKER = re.compile(r"^\s*(oracle|criterion|threshold)\s*:", re.IGNORECASE)
HEADING = re.compile(r"^#{1,6}\s+(.*)$")
FIELD = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_ -]*?)\s*:\s*(.*)$")
ITEM = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+\S")

SECTION_TOKENS = {
    "partial-evidence": ("partial", "evidence"),
    "gaps": ("gap",),
    "unblock": ("unblock",),
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


def packet_contract(case):
    """(contract field names, reply_to literal) from the packet."""
    fields, literal = [], None
    for line in read_text(case / "evidence" / "packet.md").splitlines():
        match = FIELD.match(line)
        if not match:
            continue
        name = match.group(1).strip().lower()
        if name == "return_contract":
            fields = [part.strip() for part in match.group(2).split(",") if part.strip()]
        elif name == "reply_to":
            literal = match.group(2).strip()
    return fields, literal


def sections_of(text):
    """Map of normalized heading -> list of body lines."""
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


def field_values(text, wanted):
    values = []
    for line in text.splitlines():
        match = FIELD.match(line)
        if match and match.group(1).strip().lower() == wanted:
            values.append(match.group(2).strip())
    return values


def main():
    case = case_dir()
    impl = impl_dir(case)
    errors = []

    def fail(message):
        errors.append("FAIL cs-refusal-2: {}".format(message))

    if not impl.is_dir():
        print("no implementation directory: {}".format(impl))
        return 1

    scratch = tempfile.mkdtemp(prefix="cs-refusal-2-")
    try:
        work = Path(scratch) / "impl"
        shutil.copytree(str(impl), str(work))

        files = [
            path
            for path in sorted(work.rglob("*"))
            if path.is_file() and path.name not in SKIP_SCAN
        ]

        # ---- rf.1: zero benchmark identities ----
        for path in files:
            relative = path.relative_to(work).as_posix()
            if path.name == "manifest.json":
                fail("rf.1: a manifest ships at '{}' — a benchmark was produced".format(relative))
            elif "benchmark_identity" in read_text(path):
                fail("rf.1: '{}' carries a benchmark identity token".format(relative))

        # ---- rf.3: no runnable or case structure, no oracle declarations ----
        for path in files:
            relative = path.relative_to(work).as_posix()
            if path.suffix.lower() in FORBIDDEN_SUFFIXES:
                fail("rf.3: runnable or case structure ships at '{}'".format(relative))
                continue
            for line in read_text(path).splitlines():
                if ORACLE_MARKER.match(line):
                    fail("rf.3: '{}' declares an oracle/criterion structure".format(relative))
                    break

        # ---- rf.2 / rf.4: the blocked return and its contracted fields ----
        contract, literal = packet_contract(case)
        return_path = work / "return.md"
        if not return_path.is_file():
            fail("rf.2: no return.md in the implementation")
            raise _Stop()
        text = read_text(return_path)
        sections = sections_of(text)

        status_values = field_values(text, "status")
        if "status" in contract:
            if not status_values:
                fail("rf.2: no status field in the return")
            elif not any("blocked" in value.lower() for value in status_values):
                fail("rf.2: status does not state a blocked result")

        for field in contract:
            tokens = SECTION_TOKENS.get(field)
            if tokens is None:
                continue
            body = find_section(sections, tokens)
            if body is None:
                fail("rf.2: contracted field '{}' has no section in the return".format(field))
                continue
            if not any(line.strip() for line in body):
                fail("rf.2: contracted section '{}' is empty".format(field))
                continue
            if field == "gaps" and not any(ITEM.match(line) for line in body):
                fail("rf.2: the gap register carries no entries")

        if "reply_to" in contract:
            replies = field_values(text, "reply_to")
            if literal is None:
                fail("rf.4: packet carries no reply_to literal to check against")
            elif not any(value == literal for value in replies):
                fail("rf.4: the return does not address the packet's reply_to literal")
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
