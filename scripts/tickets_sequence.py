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

if __package__:
    from .packs import PackError, resolve_pack
    from .tickets_markdown import dequote
    from .tickets_registry import EXECUTOR_REGISTRY
else:  # pragma: no cover - direct/installed script path
    from packs import PackError, resolve_pack
    from tickets_markdown import dequote
    from tickets_registry import EXECUTOR_REGISTRY

try:
    from . import state_root
except ImportError:
    import state_root

SEQUENCE_NAME_RE = re.compile(r"^orch-[a-z][a-z-]*$")
PROJECT_SKILL_RE = re.compile(r"^project:[a-z][a-z0-9-]*$")
STAGE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SKILL_TIERS = ("instances", "kernel", "engines", "workflows", "utilities")
FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.DOTALL)
ROLE_RE = re.compile(r"^role:\s*([A-Za-z][A-Za-z0-9_-]*)\s*$", re.MULTILINE)
# The two role-bearing capability classes of ``rules/roles.md`` clause 2.
# ``none`` declares no role at all, so it never disagrees with a head.
ROLE_BEARING = ("planner", "worker")


def _normalized_entries(declared):
    """Return frontmatter sequence entries with the ticket spelling rules."""

    return [dequote(entry) for entry in declared]


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


def _skill_manifest(name: str) -> Optional[Path]:
    """The one resolved ``SKILL.md`` behind a sequence entry, or ``None``.

    Both resolution questions this module asks -- does the entry name a
    skill that exists, and what role does that skill declare -- read the
    same file, so they resolve it once here.
    """

    if name.startswith("project:"):
        skill_name = name.split(":", 1)[1]
        current = Path.cwd().resolve()
        for directory in (current, *current.parents):
            candidate = directory / ".orchflows" / "skills" / skill_name / "SKILL.md"
            if candidate.is_file():
                return candidate
        return None
    for root in _source_skill_roots():
        for tier in SKILL_TIERS:
            candidate = root / tier / name / "SKILL.md"
            if candidate.is_file():
                return candidate
    return None


def _declared_role(name: str) -> Optional[str]:
    """The ``role:`` a resolved skill declares for itself, or ``None``."""

    manifest = _skill_manifest(name)
    if manifest is None:
        return None
    try:
        text = manifest.read_text(encoding="utf-8")
    except OSError:
        return None
    block = FRONTMATTER_RE.match(text)
    if block is None:
        return None
    match = ROLE_RE.search(block.group(1))
    return match.group(1) if match else None


def _head_role(executor: str) -> Optional[str]:
    """The role a chain's head establishes for the whole chain.

    The registry is the authority for a callable verb; a project-scoped
    head has none, so its own declaration answers instead.
    """

    name = dequote(executor)
    if not name:
        return None
    registered = EXECUTOR_REGISTRY.get(name)
    if registered is not None:
        return registered.get("role")
    return _declared_role(name)


def sequence_role_findings(declared, executor) -> list:
    """Warning-level findings for a skill chain whose continuations
    declare a role the head's binding will not give them.

    Not a defect: ``rules/roles.md`` clause 4 makes a continuation's own
    ``role:`` inert by law, so the chain is lawful and the caller has
    already accepted the head's binding by ordering it. What the caller
    may not have noticed is the consequence -- a planner-declared skill
    run inside a worker child renders no independent verdict -- and that
    is what each finding names.
    """

    if not isinstance(declared, list):
        return []
    entries = _normalized_entries(declared)
    if len(entries) < 2 or not all(_is_skill_name(entry) for entry in entries):
        return []
    head_role = _head_role(executor or entries[0])
    if head_role not in ROLE_BEARING:
        return []
    findings = []
    for entry in entries[1:]:
        role = _declared_role(entry)
        if role not in ROLE_BEARING or role == head_role:
            continue
        findings.append({
            "code": "sequence-role-mismatch",
            "severity": "warning",
            "entry": entry,
            "declared_role": role,
            "head_role": head_role,
            "message": (
                f"sequence continuation '{entry}' declares role '{role}' and runs "
                f"at the head's '{head_role}' binding instead; its own `role:` has "
                "no dispatch effect (rules/roles.md §4), so anything it renders over "
                "this chain's own work carries no fresh independent verdict "
                "(rules/verification.md §11) — a step needing one is its own ticket."
            ),
        })
    return findings


def _skill_resolution_defect(entry: str) -> Optional[str]:
    if entry.startswith("project:"):
        if not PROJECT_SKILL_RE.fullmatch(entry):
            return f"sequence entry '{entry}' is not a valid project skill name"
        if _skill_manifest(entry) is None:
            return f"sequence skill '{entry}' does not resolve from the project scope"
        return None
    if not SEQUENCE_NAME_RE.fullmatch(entry):
        return f"sequence entry '{entry}' is not an exact skill name"
    if _skill_manifest(entry) is None:
        return f"sequence skill '{entry}' does not resolve under skills/"
    return None


def _pack_options(canonical_root=None, project_root=None, user_root=None):
    return {
        "canonical_root": canonical_root,
        "project_root": project_root,
        "user_root": user_root,
    }


def _cell_resolution_defects(
    entries: list[str],
    pack,
    *,
    canonical_root=None,
    project_root=None,
    user_root=None,
) -> list[str]:
    if not str(pack or "").strip():
        return ["cell sequence requires a stamped pack to resolve its stages"]
    if "{{" in str(pack):
        return []
    try:
        resolved = resolve_pack(
            pack,
            **_pack_options(
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
        expected_executor = dequote(executor)
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
    lines.extend(
        finding["message"]
        for finding in sequence_role_findings(declared, loaded.get("executor"))
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
    "ROLE_BEARING",
    "SEQUENCE_NAME_RE",
    "STAGE_NAME_RE",
    "sequence_block",
    "sequence_defects",
    "sequence_role_findings",
)
