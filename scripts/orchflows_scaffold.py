#!/usr/bin/env python3
"""Minimal valid skeletons for `orchflows new`.

One file per kind, and nothing beyond what its own admission requires: a
skeleton that guessed at content would be a second, weaker copy of the
authoring standard. Every skeleton is a *valid* item on the day it is
written -- a pack carries all four cells and every mandatory craft
section, a workflow carries a manifest and one stub -- so the first thing
an author does is edit, never repair.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

try:
    from scripts import rings
except ImportError:  # pragma: no cover - direct/installed flat script path
    import rings


AUTHORING_DOC = "docs/custom-workflow-authoring.md"

_SKILL = """---
name: {name}
description: One sentence saying when to use {name} and what it returns.
---

# {name}

State what this skill does, in the imperative, to the agent that runs it.

## Steps

1. Replace this with the first step.

Return: what the caller gets back.
"""

# The craft's mandatory `##` sections come from contracts/pack-signature.md;
# the skeleton carries every one as an empty anchor rather than inventing
# domain content, because an absent section is a shape defect and invented
# content is worse than none.
_CRAFT_SECTIONS = (
    ("Vocabulary", "Define this domain's terms once, here."),
    ("Workspace", "Identities, isolation, candidate diffs, conflict handling."),
    ("Spec fields", "What a spec must carry before decomposition accepts it."),
    ("Outline", "What a well-formed frozen root carries in this domain."),
    ("Slicing", "How a spec cuts into work items here."),
    ("Evidence", "Evidence methods and identities a checker may challenge."),
    ("Lens", "This domain's review criteria."),
)

_PACK = """---
name: {name}
description: Domain pack for <artifacts>. Stamp when the deliverable is <kind>.
---

# {name}

| cell | binding |
| --- | --- |
| adapter | git |
| stages | [build] |
| assembly | none |
| craft | the domain document at [craft](references/craft.md) |
"""

_WORKFLOW = """---
name: {name}
description: One sentence saying what running {name} produces.
entry: {name}
placeholders: [run]
---

# {name}

What this workflow produces, and what the caller supplies. Instantiate it
with `tickets.py instantiate {name} --run <run>`.
"""

_WORKFLOW_STUB = """---
id: 00-root
run: {{{{run}}}}
status: pending
executor: orch-slice
depends_on: []
bound: 60m
---

## Goal

One observable end result.

## Context

What the executor needs and nothing more.

## Report

"""


def _craft(name: str) -> str:
    body = [f"# {name} craft", ""]
    for heading, prompt in _CRAFT_SECTIONS:
        body.extend([f"## {heading}", "", prompt, ""])
    return "\n".join(body)


def files_for(kind: str, name: str) -> List[Tuple[str, str]]:
    """``[(relative path, text)]`` for one new item, in write order."""

    kind = rings.kind_of(kind)
    name = rings.item_name(name)
    if kind == "skill":
        return [("SKILL.md", _SKILL.format(name=name))]
    if kind == "pack":
        return [
            ("SKILL.md", _PACK.format(name=name)),
            ("references/craft.md", _craft(name)),
        ]
    return [
        ("template.md", _WORKFLOW.format(name=name)),
        ("00-root.md", _WORKFLOW_STUB),
    ]


def write(directory: Path, kind: str, name: str) -> List[Path]:
    """Write one skeleton under ``directory/<name>``. Refuses to overwrite."""

    target = Path(directory) / rings.item_name(name)
    written = []
    for relative, text in files_for(kind, name):
        path = target / relative
        if path.exists():
            raise rings.RingError("item-exists", f"already there: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        # Bytes for LF on every host: `write_text(newline=...)` is 3.10+.
        path.write_bytes(text.encode("utf-8"))
        written.append(path)
    return written


def sections() -> Dict[str, str]:
    """The mandatory craft anchors this scaffold writes, as data for a test."""

    return dict(_CRAFT_SECTIONS)


__all__ = ("AUTHORING_DOC", "files_for", "sections", "write")
