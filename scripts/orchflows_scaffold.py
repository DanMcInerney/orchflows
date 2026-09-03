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

import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from scripts import rings
except ImportError:  # pragma: no cover - direct/installed flat script path
    import rings


AUTHORING_DOC = "docs/custom-workflow-authoring.md"

# An applied skill is entered by a child `--skill` establishes, and
# `rules/roles.md` clause 6 says that child is of the skill's own declared
# role -- so a skill without one, or carrying `role: none`, is refused at
# dispatch. `worker` is what an applied skill does unless its author says
# otherwise: execution, the role the verb `orch-do` itself declares.
_SKILL = """---
name: {name}
description: One sentence saying when to use {name} and what it returns.
role: worker
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


# A sheet is extra craft stamped beside a pack, so its skeleton is the one
# that cannot be domain-blind the way the others are: it has to name a pack
# that resolves in this installation and key its `## Lens` by a kind that
# pack's adapter emits, or `write` scaffolds a sheet the validator refuses
# and no ticket could stamp. Both facts are read from the installed packs
# below rather than spelled here -- a pack name written into this module
# would be a domain name inside machinery, which `tools/validate.py`
# refuses, and would go stale the day that pack is renamed.
_SHEET = """---
name: {name}
description: One sentence saying when to stamp {name} beside its pack.
packs: [{pack}]
---

# {name}

## Craft

What this sheet adds to the stamped pack's craft for the maker. Additive
and tighten-only: never loosen what the craft already requires.

## Lens

### {kind}

What a judge checks here beside the craft's own `### {kind}` entry.
"""


# A bundle's manifest describes the ring it sits in, not an item inside it
# (contracts/bundle.md), so it is the one skeleton written beside the item
# directories rather than into a new `<name>/`. `requires: []` is written
# out rather than omitted: an author adding a requirement edits a line that
# is already the right shape.
_BUNDLE = """---
name: {name}
version: {version}
requires: []
---

# {name}

What this bundle is for, who maintains it, and what a consumer gets by
importing it. Each requirement above is one <git-url>@<tag-or-sha>.
"""


def _sheet_binding():
    """`(pack, artifact kind)` the sheet skeleton is written against.

    The first pack resolvable from here by name, and the kind its own
    adapter emits. Deterministic, so two scaffolds in one installation
    agree; refused rather than guessed where no pack resolves, because a
    sheet with no pack is a sheet nothing may stamp.
    """

    if __package__:
        from .tickets_adapters import AdapterError, adapter_spec
    else:  # pragma: no cover - direct/installed flat script path
        from tickets_adapters import AdapterError, adapter_spec
    for record in rings.inventory(("pack",)):
        if record.get("reserved") and record.get("refusal"):
            continue
        try:
            return str(record["name"]), adapter_spec(str(record["name"])).artifact_kind
        except AdapterError:
            continue
    raise rings.RingError(
        "no-pack-to-stamp",
        "no pack resolves from here, so a sheet skeleton would name none; "
        f"install the library or author the sheet by hand against {AUTHORING_DOC}",
    )


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
    if kind == "sheet":
        pack, artifact_kind = _sheet_binding()
        return [(
            rings.MANIFESTS["sheet"],
            _SHEET.format(name=name, pack=pack, kind=artifact_kind),
        )]
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


def bundle_version() -> str:
    """The version a scaffolded manifest carries: today, as a date.

    A date is a version a person can write again tomorrow without a release
    process, and `contracts/bundle.md` takes either that or a tag.
    """

    return datetime.date.today().isoformat()


def write_bundle(ring: Path, name: str, version: Optional[str] = None) -> Path:
    """Write one bundle manifest into ``ring``. Refuses to overwrite."""

    path = Path(ring) / rings.BUNDLE_MANIFEST
    if path.exists():
        raise rings.RingError("bundle-exists", f"already there: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _BUNDLE.format(
        name=rings.item_name(name),
        version=version if version else bundle_version(),
    )
    # Bytes for LF on every host, as `write` does.
    path.write_bytes(text.encode("utf-8"))
    return path


def sections() -> Dict[str, str]:
    """The mandatory craft anchors this scaffold writes, as data for a test."""

    return dict(_CRAFT_SECTIONS)


def lens_entries() -> Dict[str, str]:
    """The `## Lens` artifact-kind anchors it writes, likewise."""

    return dict(_CRAFT_LENS_ENTRIES)


__all__ = (
    "AUTHORING_DOC", "bundle_version", "files_for", "lens_entries",
    "sections", "write", "write_bundle",
)
