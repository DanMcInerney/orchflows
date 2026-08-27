#!/usr/bin/env python3
"""Validate the structural shape of one sealed ticket graph.

Cut admission is semantic-shape, dependency, exact executor binding, and seal
validation. Predicted file scopes are not part of the ticket protocol; actual
diff overlap and ordinary Git conflicts are handled at integration.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

_SIBLING = str(Path(__file__).resolve().parent)
if _SIBLING not in sys.path:
    sys.path.append(_SIBLING)
import state_root
from tickets_format import _parse_frontmatter, ticket_defects

CLEAN = 0
REPORTED = 1
NO_TICKET_SET = 2


def graph_findings(texts: dict) -> list:
    findings = []
    data = {}
    for fallback_id, text in sorted(texts.items()):
        parsed = _parse_frontmatter(text)
        ticket_id = str(parsed.get("id") or fallback_id)
        if ticket_id in data:
            findings.append((ticket_id, "duplicate-id", "ticket id occurs more than once"))
        data[ticket_id] = parsed
        findings.extend((ticket_id, "ticket-shape", defect) for defect in ticket_defects(text))
    for ticket_id, parsed in sorted(data.items()):
        for dependency in parsed.get("depends_on") or []:
            if dependency not in data:
                findings.append((ticket_id, "dangling-dependency", str(dependency)))
    remaining = {ticket_id: set(parsed.get("depends_on") or []) & set(data) for ticket_id, parsed in data.items()}
    while remaining:
        ready = {ticket_id for ticket_id, dependencies in remaining.items() if not dependencies}
        if not ready:
            findings.append(("run", "dependency-cycle", ", ".join(sorted(remaining))))
            break
        for ticket_id in ready:
            del remaining[ticket_id]
        for dependencies in remaining.values():
            dependencies.difference_update(ready)
    return sorted(set(findings))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="cutcheck.py", description=__doc__)
    parser.add_argument("run")
    parser.add_argument("--baseline", required=False, help="host routing value; structural validation is revision-independent")
    parser.add_argument("--lib", required=False, help="installed library location")
    args = parser.parse_args(argv)
    run_dir = state_root.tickets_root() / args.run
    if not run_dir.is_dir():
        print(f"cutcheck: no ticket set resolved for run {args.run}")
        return NO_TICKET_SET
    try:
        texts = {path.stem: path.read_text(encoding="utf-8") for path in sorted(run_dir.glob("*.md"))}
    except (OSError, UnicodeDecodeError) as error:
        print(f"cutcheck: {error}")
        return NO_TICKET_SET
    findings = graph_findings(texts)
    for ticket_id, code, detail in findings:
        print(f"{ticket_id}: {code}: {detail}")
    if findings:
        return REPORTED
    print("cutcheck: no structural finding")
    return CLEAN


if __name__ == "__main__":
    raise SystemExit(main())
