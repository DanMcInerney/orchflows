"""Validate and render one-child skill or pack-cell execution sequences.

The ticket's sequence is deliberately one of two closed forms. Skill
chains name callable skills (canonical ``orch-*`` names or project-scoped
``project:<name>`` names); cell chains name only the stages exposed by the
ticket's resolved pack. A chain never mixes the two forms, and neither
form creates another dispatch or changes the role established for the one
child.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

try:
    from .packs import PackError, resolve_pack
except ImportError:
    try:
        from packs import PackError, resolve_pack
    except ImportError:
        class PackError(ValueError):
            """Fallback used when a flat command omits the pack resolver."""

            def __init__(self, code: str, detail: str):
                super().__init__(detail)
                self.code = code
                self.detail = detail

        resolve_pack = None

try:
    from . import state_root
except ImportError:
    import state_root

SEQUENCE_NAME_RE = re.compile(r"^orch-[a-z][a-z-]*$")
PROJECT_SKILL_RE = re.compile(r"^project:[a-z][a-z0-9-]*$")
STAGE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _normalized_entries(declared):
    """Return frontmatter sequence entries with the ticket spelling rules."""

    return [str(entry).strip().strip("`").strip() for entry in declared]


def _is_skill_name(entry: str) -> bool:
    return isinstance(entry, str) and bool(
        SEQUENCE_NAME_RE.fullmatch(entry) or PROJECT_SKILL_RE.fullmatch(entry)
    )


def _is_stage_name(entry: str) -> bool:
    return isinstance(entry, str) and bool(STAGE_NAME_RE.fullmatch(entry)) and not _is_skill_name(entry)


def _source_skill_roots() -> tuple[Path, ...]:
    """Return canonical/installed roots in which a skill can be resolved."""

    here = Path(__file__).resolve()
    roots = []
    if here.parent.name == "scripts":
        roots.append(here.parent.parent / "skills")
    roots.extend((here.parent.parent / "lib" / "skills",))
    try:
        roots.append(state_root.state_root().parent / "lib" / "skills")
    except OSError:
        pass
    result = []
    seen = set()
    for root in roots:
        marker = str(root).casefold()
        if marker not in seen:
            seen.add(marker)
            result.append(root)
    return tuple(result)


def _canonical_skill_resolves(name: str) -> bool:
    return any(
        (root / tier / name / "SKILL.md").is_file()
        for root in _source_skill_roots()
        for tier in ("instances", "kernel", "engines", "workflows", "utilities")
    )


def _project_skill_resolves(name: str) -> bool:
    """Resolve ``project:<name>`` from the nearest project scope."""

    skill_name = name.split(":", 1)[1]
    current = Path.cwd().resolve()
    for directory in (current, *current.parents):
        candidate = directory / ".orchflows" / "skills" / skill_name / "SKILL.md"
        if candidate.is_file():
            return True
    return False


def _skill_resolution_defect(entry: str) -> Optional[str]:
    if entry.startswith("project:"):
        if not PROJECT_SKILL_RE.fullmatch(entry):
            return f"sequence entry '{entry}' is not a valid project skill name"
        if not _project_skill_resolves(entry):
            return f"sequence skill '{entry}' does not resolve from the project scope"
        return None
    if not SEQUENCE_NAME_RE.fullmatch(entry):
        return f"sequence entry '{entry}' is not an exact skill name"
    if not _canonical_skill_resolves(entry):
        return f"sequence skill '{entry}' does not resolve under skills/"
    return None


def _pack_options(pack_root=None, canonical_root=None, project_root=None, user_root=None):
    options = {
        "canonical_root": canonical_root,
        "project_root": project_root,
        "user_root": user_root,
    }
    if pack_root is not None:
        options["root"] = pack_root
    return options


def _cell_resolution_defects(
    entries: list[str],
    pack,
    *,
    pack_root=None,
    canonical_root=None,
    project_root=None,
    user_root=None,
) -> list[str]:
    if not str(pack or "").strip():
        return ["cell sequence requires a stamped pack to resolve its stages"]
    if "{{" in str(pack):
        return []
    if resolve_pack is None:
        return [f"cell sequence pack '{pack}' cannot resolve stages: pack resolver unavailable"]
    try:
        resolved = resolve_pack(
            pack,
            **_pack_options(
                pack_root,
                canonical_root,
                project_root,
                user_root,
            ),
        )
    except PackError as error:
        return [f"cell sequence pack '{pack}' cannot resolve stages: {error.detail}"]
    stages = resolved.get("cells", {}).get("stages")
    if not isinstance(stages, list):
        return [f"cell sequence pack '{pack}' has no resolved stages list"]
    return [
        f"sequence stage '{entry}' is not a declared stage of pack '{pack}'"
        for entry in entries
        if entry not in stages
    ]


def sequence_defects(
    declared,
    executor: str,
    pack=None,
    *,
    pack_root=None,
    canonical_root=None,
    project_root=None,
    user_root=None,
) -> list:
    """Every way a frontmatter ``sequence`` is not a lawful chain.

    A skill sequence is an ordered list of resolvable callable names and must
    begin with the ticket's executor. A cell sequence is an ordered list of
    plain stage names declared by the ticket's resolved pack. The executor
    remains the one dispatch head for a cell sequence; stage names are data,
    not host skill bindings.
    """

    if declared is None:
        return []
    if not isinstance(declared, list):
        return ["frontmatter 'sequence' must be a list of exact skill names or pack stages"]
    entries = _normalized_entries(declared)
    defects = []
    if len(entries) < 2:
        defects.append("'sequence' with fewer than two skills or stages is the plain executor: drop the field")
        return defects

    skill_entries = [entry for entry in entries if _is_skill_name(entry)]
    cell_entries = [entry for entry in entries if _is_stage_name(entry)]
    invalid_entries = [
        entry for entry in entries if entry not in skill_entries and entry not in cell_entries
    ]
    if invalid_entries:
        defects.extend(
            f"sequence entry '{entry}' is neither an exact skill name nor a plain pack stage"
            for entry in invalid_entries
        )
    if skill_entries and cell_entries:
        defects.append("sequence mixes skill names and pack stages; choose exactly one sequence form")
        return defects
    if invalid_entries:
        return defects

    if skill_entries:
        if len(set(entries)) != len(entries):
            defects.append("'sequence' repeats a skill: each chain entry runs once")
        expected_executor = str(executor or "").strip().strip("`").strip()
        if entries and entries[0] != expected_executor:
            defects.append(
                f"sequence head '{entries[0]}' is not the ticket's executor '{expected_executor}': "
                "the chain's first skill is the `executor` every dispatcher resolves"
            )
        defects.extend(
            defect for entry in entries
            if (defect := _skill_resolution_defect(entry)) is not None
        )
        return defects

    if len(set(entries)) != len(entries):
        defects.append("'sequence' repeats a stage: each chain entry runs once")
    defects.extend(
        _cell_resolution_defects(
            entries,
            pack,
            pack_root=pack_root,
            canonical_root=canonical_root,
            project_root=project_root,
            user_root=user_root,
        )
    )
    return defects


def _sequence_form(entries: list[str]) -> str:
    if entries and all(_is_skill_name(entry) for entry in entries):
        return "skill"
    if entries and all(_is_stage_name(entry) for entry in entries):
        return "cell"
    return "mixed"


def sequence_block(loaded: dict) -> list:
    """Prompt lines for a ticket whose frontmatter states a ``sequence``."""

    declared = loaded.get("sequence")
    if not isinstance(declared, list):
        return []
    entries = _normalized_entries(declared)
    if len(entries) < 2:
        return []
    ordered = ", then ".join(entries)
    form = _sequence_form(entries)
    if form == "cell":
        lines = [
            f"This ticket states a pack-cell execution sequence: apply stages {ordered} "
            "in this declared order; stages are pack data, not host skill bindings "
            "(contracts/pack-signature.md).",
        ]
    else:
        lines = [
            f"This ticket states an executor sequence: apply {ordered} — each "
            "exact named skill completed and its return filed before the next "
            "begins, all in this one context; never re-dispatch any of them "
            "(rules/delegation.md §4).",
        ]
        index = _by_name_root()
        where = (
            str(index / '<name>' / 'SKILL.md')
            if index is not None
            else "the library's by-name index"
        )
        lines.append(
            f"Read each continuation skill's contract directly from {where}; "
            "invoking it by name forks a packet-less child that must refuse."
        )
    lines.append(
        "This chain runs at its head's binding, the role established by its "
        "head executor; a continuation's own `role:` has no dispatch effect, "
        "so the caller choosing this order accepts that binding "
        "(rules/roles.md §4)."
    )
    lines.append(
        "The chain is one witness: a verdict you render on work this chain "
        "changed is void (rules/verification.md §11) — file it as work, and "
        "leave acceptance to the context outside your assigned name that "
        "this ticket's independence path names."
    )
    return lines


def _by_name_root():
    """The installed flat index, or ``None`` from a bare checkout."""

    try:
        root = state_root.state_root().parent / "lib" / "by-name"
    except OSError:
        return None
    return root if root.is_dir() else None


__all__ = (
    "PROJECT_SKILL_RE",
    "SEQUENCE_NAME_RE",
    "STAGE_NAME_RE",
    "sequence_block",
    "sequence_defects",
)
