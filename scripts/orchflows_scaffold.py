#!/usr/bin/env python3
"""Minimal valid skeletons for `orchflows new`.

One file per kind, and nothing beyond what its own admission requires: a
skeleton that guessed at content would be a second, weaker copy of the
authoring standard. Every skeleton is a *valid* item on the day it is
written -- a pack carries all four cells and every mandatory craft
section, a workflow carries a frame open, one callable call and a close --
so the first thing an author does is edit, never repair.
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
    ("Lens", "One `###` entry per artifact kind; criteria for each."),
)

# `## Lens`'s `###` entries, keyed by artifact kind. `root` and `cut` are
# library-owned; the third is the kind the pack's adapter emits, and the
# skeleton's `git` goes with the `adapter | git` row `_PACK` writes.
_CRAFT_LENS_ENTRIES = (
    ("root", "What a well-formed frozen root carries in this domain."),
    ("cut", "How a spec cuts into work items here."),
    ("git", "What a finished deliverable must satisfy, what proves it, "
            "and which findings block."),
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
disable-model-invocation: true
---

Require: what the caller supplies before {name} can start.

    tickets.py frame-open <run> --goal-file <goal> --workflow {name}

Re-read the frame's `## Report` and its children before each wave, then
append that wave's decision with `tickets.py result <run> <frame> --by
<frame>`. Replace the one call below with this workflow's real calls, and
keep every returned `artifact:` line verbatim.

    tickets.py do <run> --pack <pack> --parent <frame> --goal-file <goal>

Never: state a constraint here that this workflow's calls do not obey.

Return: `tickets.py frame-close <run> <frame> --done <check>`, whose done
is a command, and whose close carries a judge child or an
`unjudged: <reason>` journal line once two or more calls have run.
"""


def _craft(name: str) -> str:
    body = [f"# {name} craft", ""]
    for heading, prompt in _CRAFT_SECTIONS:
        body.extend([f"## {heading}", "", prompt, ""])
        if heading != "Lens":
            continue
        for kind, entry in _CRAFT_LENS_ENTRIES:
            body.extend([f"### {kind}", "", entry, ""])
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
    if kind == "workflow":
        return [("SKILL.md", _WORKFLOW.format(name=name))]
    # Every kind is named, and an unnamed one refuses. The tail used to
    # fall through to the workflow skeleton, so a kind added to
    # `rings.KINDS` before its skeleton existed would have written a
    # `SKILL.md` under a kind whose manifest is not that -- a wrong item
    # written silently, which is the one outcome a scaffold must not have.
    raise rings.RingError(
        "kind-unscaffolded",
        f"'orchflows new {kind}' has no skeleton yet; author the item by "
        f"hand against {AUTHORING_DOC}",
    )


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


def lens_entries() -> Dict[str, str]:
    """The `## Lens` artifact-kind anchors it writes, likewise."""

    return dict(_CRAFT_LENS_ENTRIES)


__all__ = ("AUTHORING_DOC", "files_for", "lens_entries", "sections", "write")
