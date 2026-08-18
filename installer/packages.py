"""Canonical package discovery, role rendering, and source identity."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .foundation import (
    PROFILES_MD,
    PROFILE_ROLES,
    REPO_ROOT,
    _BINDING_RE,
    _CODEX_AGENT_TYPE_RE,
)

# --- frontmatter parsing (adapters / prompts only need this much) ------


def split_frontmatter(text: str):
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise ValueError("missing frontmatter")
    end = None
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") == "---":
            end = i
            break
    if end is None:
        raise ValueError("unterminated frontmatter")
    return "".join(lines[: end + 1]), "".join(lines[end + 1 :])


def host_legal_frontmatter(frontmatter: str) -> str:
    """Host-legal subset for Claude adapter stubs: name and description
    only; orchflows-only keys (role) stay in the item file."""
    kept = [
        line
        for line in frontmatter.splitlines(keepends=True)
        if line.rstrip("\r\n") == "---"
        or line.partition(":")[0].strip() in ("name", "description")
    ]
    return "".join(kept)


def frontmatter_field(frontmatter: str, key: str):
    for line in frontmatter.splitlines():
        line_key, sep, rest = line.partition(":")
        if sep and line_key.strip() == key:
            value = rest.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            return value
    return None


def discover_packages():
    """Every skill/pack package: ``skills/<sublayer>/orch-*`` and ``packs/orch-*``."""

    packages = []
    skills_root = REPO_ROOT / "skills"
    if skills_root.is_dir():
        for sublayer in sorted(p for p in skills_root.iterdir() if p.is_dir()):
            for pkg in sorted(p for p in sublayer.iterdir() if p.is_dir()):
                skill_md = pkg / "SKILL.md"
                if skill_md.is_file():
                    packages.append(skill_md)
    packs_root = REPO_ROOT / "packs"
    if packs_root.is_dir():
        for pkg in sorted(p for p in packs_root.iterdir() if p.is_dir()):
            skill_md = pkg / "SKILL.md"
            if skill_md.is_file():
                packages.append(skill_md)
    return packages


TEMPLATE_MANIFEST = "template.md"


def discover_templates(root: Path = REPO_ROOT):
    """Every invocable composition: a template directory
    ``compositions/<name>/`` whose ``template.md`` manifest carries an
    ``entry`` (per contracts/work-item.md's Template and stub section).

    Returns ``(directory, frontmatter, body)`` per template. A directory
    without a manifest, or a manifest without frontmatter or without
    ``entry``, is library data rather than a name surface and is skipped
    -- it still reaches the installed lib copy. ``compositions/references/``
    is exactly that."""

    templates = []
    comps_root = root / "compositions"
    if not comps_root.is_dir():
        return templates
    for directory in sorted(p for p in comps_root.iterdir() if p.is_dir()):
        manifest = directory / TEMPLATE_MANIFEST
        if not manifest.is_file():
            continue
        try:
            frontmatter, body = split_frontmatter(manifest.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if not frontmatter_field(frontmatter, "entry"):
            continue
        templates.append((directory, frontmatter, body))
    return templates


def template_adapter_body(name: str, lib_template_dir: Path, frontmatter: str) -> str:
    """The Claude adapter stub's body for a template.

    A skill's adapter is an ``@``-include of one file; a template is a
    directory, and ``@`` cannot include one -- so the stub says what the
    name is and hands over the two commands that run it. The placeholders
    come from the manifest's own declaration, so a stub can never offer a
    ``--set`` the template does not take."""

    declared = (frontmatter_field(frontmatter, "placeholders") or "").strip()
    names = [item.strip() for item in declared.strip("[]").split(",") if item.strip()]
    sets = "".join(f" --set {item}=<{item}>" for item in names)
    return (
        f"`{name}` is a ticket-set template, not a skill body: a directory of\n"
        f"ticket stubs at {lib_template_dir}, with its manifest and every\n"
        "stub's objective, write scope and completion test beside it. Read the\n"
        "manifest first. Instantiate it into one run:\n\n"
        f"    tickets.py instantiate {lib_template_dir} --run <run>{sets}\n\n"
        "then run `orch-frontier` over that run, which drains the stubs by\n"
        "their `depends_on` edges. The terminal stub's completion test is this\n"
        "template's done check.\n"
    )


# --- host role agents, parsed from the canonical table -----------------


def _parse_binding(cell: str) -> dict:
    return {match.group("key"): match.group("value") for match in _BINDING_RE.finditer(cell)}


def load_role_profiles(profiles_md_path: Path = PROFILES_MD):
    text = profiles_md_path.read_text(encoding="utf-8")
    profiles = {}
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 4 or not cells[0].startswith("`orch-"):
            continue
        name = cells[0].strip("`")
        role = cells[1]
        if role not in PROFILE_ROLES:
            continue
        profiles[name] = {"role": role, "codex": _parse_binding(cells[2]), "claude": _parse_binding(cells[3])}
    missing = [f"orch-{role}" for role in PROFILE_ROLES if f"orch-{role}" not in profiles]
    if missing:
        raise ValueError(f"{profiles_md_path}: missing role profile row(s) for {', '.join(missing)}")
    codex_agent_types = set()
    for name, profile in profiles.items():
        if not {"agent_type", "model", "model_reasoning_effort"} <= set(profile["codex"]):
            raise ValueError(f"{profiles_md_path}: incomplete Codex binding for {name}")
        agent_type = profile["codex"]["agent_type"]
        if _CODEX_AGENT_TYPE_RE.fullmatch(agent_type) is None:
            raise ValueError(f"{profiles_md_path}: invalid Codex agent_type for {name}: {agent_type}")
        if agent_type in codex_agent_types:
            raise ValueError(f"{profiles_md_path}: duplicate Codex agent_type: {agent_type}")
        codex_agent_types.add(agent_type)
        if "model" not in profile["claude"]:
            raise ValueError(f"{profiles_md_path}: incomplete Claude binding for {name}")
    return profiles


def _role_description(name: str) -> str:
    """The routing fact and nothing else. It used to add "follow the role
    contract at <roles.md>": an imperative with no addressee, listed on
    every turn to every context holding the Agent tool -- children
    included -- while the dispatcher's law is already reached through
    rules/roles.md section 4 (contracts/work-item.md, orch-frontier)."""

    return f"Orchflows child role {name}."


# What a rendered role agent instructs, and all it instructs. It opened by
# sending every child of every role to read rules/roles.md before acting --
# 149 words loaded before the child had read its own ticket, whose own text
# already carries the clauses a child acts on (stay in scope; write the
# return into the durable artifact; deliver it by SendMessage). No rendered
# role agent file names roles.md anywhere (D-2).
ROLE_INSTRUCTIONS = "Stay within the delegated scope."

def render_codex_agent(name: str, profile: dict) -> str:
    binding = profile["codex"]
    lines = [
        f"name = {json.dumps(binding['agent_type'])}",
        f"description = {json.dumps(_role_description(name))}",
        f"developer_instructions = {json.dumps(ROLE_INSTRUCTIONS)}",
        f"model = {json.dumps(binding['model'])}",
        f"model_reasoning_effort = {json.dumps(binding['model_reasoning_effort'])}",
    ]
    if binding.get("service_tier"):
        lines.append(f"service_tier = {json.dumps(binding['service_tier'])}")
    return "\n".join(lines) + "\n"


def render_claude_agent(name: str, profile: dict) -> str:
    binding = profile["claude"]
    lines = [
        "---",
        f"name: {name}",
        f"description: {json.dumps(_role_description(name))}",
        f"model: {binding['model']}",
    ]
    if binding.get("effort"):
        lines.append(f"effort: {binding['effort']}")
    claude_transport = (
        " Write your contracted return into the dispatch's durable artifact, then "
        "deliver it or a pointer to it via SendMessage to your spawner as your final "
        "action - plain final text is not delivered to your caller."
    )
    lines.extend(["---", "", ROLE_INSTRUCTIONS + claude_transport])
    return "\n".join(lines) + "\n"


# --- managed marker blocks ----------------------------------------------


def template_markers(template_text: str):
    lines = [line.strip() for line in template_text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("empty host-block template")
    return lines[0], lines[-1]


def resolved_python_interpreter() -> str:
    """The interpreter install.py verified itself running under
    (``sys.executable``). Refuses when the platform reports none rather than
    rendering a bare ``python`` into every command the host block hands an
    agent: on Windows that name is commonly the Store stub, so the fallback
    shipped a command that fails on first use."""

    if not sys.executable:
        raise ValueError(
            "this platform reports no sys.executable, so no interpreter path "
            "can be rendered into the host block; rerun install.py with an "
            "interpreter that reports one"
        )
    return sys.executable


def _git_dirs(repo_root: Path) -> tuple[Path, Path] | None:
    """``(git_dir, common_dir)`` for a checkout, or ``None`` when neither can
    be read. In an ordinary clone both are ``<root>/.git``. In a git worktree
    (``.git`` is a *file* holding ``gitdir: <path>``) HEAD lives in that
    gitdir while ``refs/`` and ``packed-refs`` live in the shared checkout the
    gitdir's ``commondir`` names — so the two differ, and reading HEAD's ref
    from the wrong one is why a worktree install used to record no commit."""

    marker = repo_root / ".git"
    if marker.is_dir():
        return marker, marker
    if not marker.is_file():
        return None
    try:
        pointer = marker.read_text(encoding="utf-8")
    except OSError:
        return None
    named = ""
    for line in pointer.splitlines():
        if line.startswith("gitdir:"):
            named = line.partition(":")[2].strip()
            break
    if not named:
        return None
    git_dir = Path(named)
    if not git_dir.is_absolute():
        git_dir = repo_root / git_dir
    common_file = git_dir / "commondir"
    common_dir = git_dir
    if common_file.is_file():
        try:
            common = Path(common_file.read_text(encoding="utf-8").strip())
        except OSError:
            return None
        if common.parts:
            common_dir = common if common.is_absolute() else git_dir / common
    return git_dir, common_dir


def resolve_source_commit(repo_root: Path = REPO_ROOT) -> str | None:
    """The git HEAD commit of the repo this installer runs from, read directly
    from ``.git`` (no subprocess, no dependency on ``git`` being on PATH).
    Handles both a clone and a worktree checkout (``_git_dirs``). Returns
    ``None`` whenever no checkout can be read — absent ``.git``, a gitdir
    pointer that does not parse, a ref that resolves to nothing, or any I/O
    error."""

    dirs = _git_dirs(repo_root)
    if dirs is None:
        return None
    git_dir, common_dir = dirs
    head_file = git_dir / "HEAD"
    if not head_file.is_file():
        return None
    try:
        content = head_file.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not content:
        return None
    if not content.startswith("ref:"):
        return content
    ref = content.split(":", 1)[1].strip()
    for root in (git_dir, common_dir):
        ref_path = root / ref
        if ref_path.is_file():
            try:
                sha = ref_path.read_text(encoding="utf-8").strip()
            except OSError:
                return None
            return sha or None
    packed_refs = common_dir / "packed-refs"
    if not packed_refs.is_file():
        return None
    try:
        lines = packed_refs.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        if not line or line[0] in "#^":
            continue
        parts = line.split()
        if len(parts) == 2 and parts[1] == ref:
            return parts[0]
    return None


def source_commit_warning(commit: str | None, repo_root: Path = REPO_ROOT) -> str | None:
    """One line, when the receipt's ``source_commit`` is null, naming which
    read came up empty — otherwise a null reads as 'this installer has no such
    field' and the missing drift report looks like agreement."""

    if commit:
        return None
    dirs = _git_dirs(repo_root)
    if dirs is None:
        reason = f"no readable .git in {repo_root}"
    else:
        reason = f"HEAD in {dirs[0]} resolves to no commit"
    return f"warning: source commit unresolved ({reason}); the next install cannot report drift"


def source_commit_drift_message(old_receipt: dict | None, new_commit: str | None) -> str | None:
    """``None`` unless both receipts name a commit and they differ — first
    installs and unavailable commits are not drift."""

    old_commit = (old_receipt or {}).get("source_commit")
    if old_commit and new_commit and old_commit != new_commit:
        return f"source commit drift: {old_commit} -> {new_commit}"
    return None


