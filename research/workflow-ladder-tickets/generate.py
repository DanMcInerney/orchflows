#!/usr/bin/env python3
"""Derive one goal file and one details file per unit from the spec.

The spec is the owner; these files are its projection for
``tickets.py do --goal-file <unit>.goal.md --details-file <unit>.details.md``.
Re-run after editing the spec:

    uv run --no-project python research/workflow-ladder-tickets/generate.py
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = HERE.parent / "workflow-ladder-spec-2026-09-02.md"
# Spec sections a unit's child reads beyond section 0, section 2 and its own unit.
EXTRA = {
    "U4": "sections 7 and 8 (the layout and dependency facts the docs must state)",
    "U9": "section 7 (where a bundle manifest sits)",
    "U11": "section 7 (what the repo's own bundle may hold)",
    "U12": "section 8 (the three dependency classes and the edge-case table)",
}
MECHANICAL_DONE = "uv run --no-project python tools/run_required.py"
UNIT_HEADING = re.compile(r"\n### (U\d+[a-z]?) · ")


def paragraphs(block: str) -> dict:
    out, current = {}, None
    for para in re.split(r"\n\s*\n", block.strip()):
        match = re.match(r"\*\*(Goal|Details|Done)\.\*\*\s*(.*)", para, re.S)
        if match:
            current = match.group(1)
            out[current] = re.sub(r"\s+", " ", match.group(2)).strip()
        elif current:
            out[current] += " " + re.sub(r"\s+", " ", para).strip()
    return out


def main() -> int:
    text = SPEC.read_text(encoding="utf-8")
    pieces = UNIT_HEADING.split(text)
    if len(pieces) < 3:
        print("no units found in the spec", file=sys.stderr)
        return 1
    written = []
    for index in range(1, len(pieces), 2):
        uid, body = pieces[index], pieces[index + 1]
        title, _, rest = body.partition("\n")
        rest = rest.split("\n## 4. Order")[0]
        parts = paragraphs(rest)
        missing = {"Goal", "Details", "Done"} - parts.keys()
        if missing:
            print(f"{uid}: missing {sorted(missing)}", file=sys.stderr)
            return 1
        (HERE / f"{uid}.goal.md").write_text(parts["Goal"] + "\n", encoding="utf-8")
        reads = f"section 0 (decisions), section 2 (fixed names) and section 3 {uid}"
        if uid in EXTRA:
            reads += ", plus " + EXTRA[uid]
        details = (
            f"Unit {uid}: {title.strip()}\n\n"
            f"Spec: research/workflow-ladder-spec-2026-09-02.md. Read {reads}. "
            "The decisions in section 0 are closed: where one looks wrong, report the "
            "observation in `## Report` and continue.\n\n"
            f"{parts['Details']}\n\n"
            f"Done: {parts['Done']}\n\n"
            f"The mechanical `done` that `land` runs in the integrated tree is "
            f"`{MECHANICAL_DONE}`; run it yourself before closing. Anything in Done beyond "
            "that command is what the judge reads in your `## Report`: cite the frame id, "
            "file, or command output that shows it.\n\n"
            "Report: every file touched, every test added or changed, every name from "
            "section 2 you used, and any deviation from this unit's Details with the "
            "observation that forced it.\n"
        )
        (HERE / f"{uid}.details.md").write_text(details, encoding="utf-8")
        written.append(uid)
    print("wrote", " ".join(written))
    return 0


if __name__ == "__main__":
    sys.exit(main())
