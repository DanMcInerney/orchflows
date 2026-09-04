#!/usr/bin/env python3
"""Minimal valid skeletons for `orchflows new`.

One file per kind, and nothing beyond what its own admission requires: a
skeleton that guessed at content would be a second, weaker copy of the
authoring standard. Every skeleton is a *valid* item on the day it is
written -- a standard carries its frontmatter and every required
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
# role -- so a skill without one is refused at dispatch. `worker` is what an
# applied skill does unless its author says otherwise.
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

# A root's required `##` sections come from contracts/standard.md;
# the skeleton carries every one as an empty anchor rather than inventing
# domain content, because an absent section is a shape defect and invented
# content is worse than none.
_ROOT_SECTIONS = (
    ("Making", "What the maker does here to reach a well-formed artifact."),
    ("Vocabulary", "Define this domain's terms once, here."),
    ("Workspace", "Identities, isolation, candidate diffs, conflict handling."),
    ("Spec fields", "What a spec must carry before decomposition accepts it."),
    ("Lens", "One `###` entry per artifact kind; criteria for each."),
)

# `## Lens`'s `###` entries, keyed by artifact kind. `root` and `cut` are
# library-owned; the third is the kind the standard's adapter emits.
_ROOT_LENS_ENTRIES = (
    ("root", "What a well-formed frozen root carries in this domain."),
    ("cut", "How a spec cuts into work items here."),
    ("git", "What a finished deliverable must satisfy, what proves it, "
            "and which findings block."),
)

_ROOT = """---
name: {name}
description: Domain standard for <artifacts>. Stamp when the deliverable is <kind>.
adapter: git
---

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

    tickets.py do <run> --standard <standard> --parent <frame> --goal-file <goal>

Never: state a constraint here that this workflow's calls do not obey.

Return: `tickets.py frame-close <run> <frame> --done <check>`, whose done
is a command, and whose close carries a judge child or an
`unjudged: <reason>` journal line once two or more calls have run.
"""


# A bundle's manifest describes the ring it sits in, not an item inside it
# (contracts/bundle.md), so it is the one skeleton written beside the item
# directories rather than into a new `<name>/`. `requires: []` is written out
# rather than omitted: an author adding a requirement edits a line that is
# already the right shape.
_BUNDLE = """---
name: {name}
version: {version}
requires: []
---

# {name}

What this bundle is for, who maintains it, and what a consumer gets by
importing it. Each requirement above is one <git-url>@<tag-or-sha>.
"""


def _root_body(name: str) -> str:
    body = [f"# {name}", ""]
    for heading, prompt in _ROOT_SECTIONS:
        body.extend([f"## {heading}", "", prompt, ""])
        if heading != "Lens":
            continue
        for kind, entry in _ROOT_LENS_ENTRIES:
            body.extend([f"### {kind}", "", entry, ""])
    return "\n".join(body)


def files_for(kind: str, name: str) -> List[Tuple[str, str]]:
    """``[(relative path, text)]`` for one new item, in write order."""

    kind = rings.kind_of(kind)
    name = rings.item_name(name)
    if kind == "skill":
        return [("SKILL.md", _SKILL.format(name=name))]
    if kind == "standard":
        # The root skeleton, because a root is the domain-blind one: a
        # narrowing skeleton would have to name a broader standard that
        # resolves here, and an author who has one in mind writes `narrows:`
        # into this file and deletes the sections a narrowing is refused.
        return [(
            rings.MANIFESTS["standard"],
            _ROOT.format(name=name) + _root_body(name),
        )]
    if kind == "workflow":
        return [("SKILL.md", _WORKFLOW.format(name=name))]
    # Every kind is named, and an unnamed one refuses. A tail that fell
    # through to the workflow skeleton would write a `SKILL.md` under a kind
    # whose manifest is not that -- a wrong item written silently, which is
    # the one outcome a scaffold must not have.
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
    """The version a scaffolded manifest carries: today, as a date."""

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
    """The mandatory root anchors this scaffold writes, as data for a test."""

    return dict(_ROOT_SECTIONS)


def lens_entries() -> Dict[str, str]:
    """The `## Lens` artifact-kind anchors it writes, likewise."""

    return dict(_ROOT_LENS_ENTRIES)


__all__ = (
    "AUTHORING_DOC", "bundle_version", "files_for", "lens_entries",
    "sections", "write", "write_bundle",
)
