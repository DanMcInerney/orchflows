#!/usr/bin/env python3
"""Install orchflows for Claude Code and/or Codex from a git clone.

Stdlib-only, cross-platform (Windows + POSIX), pathlib throughout, never
symlinks. User scope is primary and auto-detects which host(s) to
configure: the Claude half runs only when ``~/.claude`` exists, the Codex
half only when ``~/.codex`` exists; if neither is found the installer
refuses with guidance instead of guessing.

- ``~/.orchflows/`` (library, scripts, receipt, the rendered
  ``host-block.md``). The library also carries a flat, host-agnostic
  ``lib/by-name/<orch-name>/SKILL.md`` index: one deterministic path per
  canonical package (every skill tier plus packs), each a redirect pointer
  to its tiered source so a name resolves without guessing a sublayer. The
  pointer never copies the body, so it carries no relative links — an agent
  follows it to the tiered file, where every ``references/`` and
  ``../../../`` link resolves from its authored location.
- Claude Code (when ``~/.claude`` exists): ``~/.claude/skills/<name>/SKILL.md``
  adapter stubs (frontmatter plus an ``@``-include of the library body),
  role agents, concurrency setting. The always-on instruction layer is
  rendered once to ``~/.orchflows/host-block.md`` (wholly installer-owned)
  and referenced from ``~/.claude/CLAUDE.md`` by one appended ``@<path>``
  import line — idempotent, migrating any legacy inline marker block found
  there from an older install.
- Codex (when ``~/.codex`` exists): prompts, four redirect skill stubs
  (``~/.codex/skills/<name>/SKILL.md`` for ``orch-spec``, ``orch-task``,
  ``orch-fix``, ``orch-build``) that point at the library instead of
  duplicating it, role agents, agent-limits config. The always-on layer
  stays an inline marker block upserted into ``~/.codex/AGENTS.md`` — a
  read-only probe (``codex debug prompt-input`` against a scratch repo,
  installed CLI 0.144.0) found ``@file`` imports do not expand there, so
  Codex keeps the proven marker-block mechanism rather than migrating to
  an import line. A preflight warns (never edits or deletes) if
  ``~/.codex/hooks.json`` references a now-missing orchflows path.

Project scope (``--project PATH``) is a thin stub: it writes only the two
managed instruction blocks (project ``CLAUDE.md``, project ``AGENTS.md``),
rendered against the *user* library paths since a project carries no
library of its own, plus a minimal receipt for those blocks. Both stay
inline marker blocks (never an import) since a project is committable and
must stay self-contained for teammates without the same ``~/.orchflows``.

The receipt records ``source_commit`` (the installed-from repo's git HEAD,
null when unavailable); a rerun whose HEAD has moved prints the drift.

``--dry-run`` builds and prints the exact same plan an install would apply,
without writing anything. ``--uninstall`` removes only unchanged generated
skill entrypoints. It prints manual cleanup for every other path in the
scope's ``receipt.json`` (gracefully, even for a receipt from an older, full
project install) and retains that receipt until cleanup is complete.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePath

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 remains supported.
    tomllib = None

REPO_ROOT = Path(__file__).resolve().parent
CANONICAL_DIRS = (
    "contracts",
    "rules",
    "docs",
    "skills",
    "packs",
    "compositions",
    "templates",
)
SCRIPT_NAMES = ("friction.py", "tickets.py", "trace.py")
PROFILES_MD = REPO_ROOT / "skills" / "kernel" / "orch-delegate" / "references" / "profiles.md"
HOST_BLOCK_TEMPLATE = REPO_ROOT / "templates" / "host-block.md"
CODEX_LIMITS_START = "# BEGIN ORCHFLOWS AGENT LIMITS"
CODEX_LIMITS_END = "# END ORCHFLOWS AGENT LIMITS"
PROFILE_ROLES = ("planner", "worker")
CODEX_SKILL_REDIRECT_NAMES = ("orch-spec", "orch-task", "orch-fix", "orch-build")
AUTO_REMOVE_KINDS = frozenset(("adapter", "prompt", "codex-skill"))
CODEX_MAX_THREADS = 20
CODEX_MAX_DEPTH = 1
CLAUDE_MAX_TOOL_USE_CONCURRENCY = 20
CLAUDE_SETTINGS_SCHEMA = "https://json.schemastore.org/claude-code-settings.json"
_BINDING_RE = re.compile(r"(?P<key>[a-z_]+)\s*`(?P<value>[^`]+)`")
_CODEX_AGENT_TYPE_RE = re.compile(r"^[a-z0-9_]+$")
_TOML_TABLE_RE = re.compile(r"^\s*\[\[?[^\]]+\]\]?\s*(?:#.*)?$")
_AGENTS_TABLE_RE = re.compile(r"^\s*\[agents\]\s*(?:#.*)?$")
_AGENTS_DOTTED_LIMIT_RE = re.compile(r"^\s*agents\.(?:max_threads|max_depth)\s*=")
_AGENTS_LIMIT_RE = re.compile(r"^\s*(?:max_threads|max_depth)\s*=")


# --- scope-derived paths -----------------------------------------------


def _require_project_root(project_root: Path | None) -> Path:
    """Narrow ``Path | None`` to ``Path`` at the one invariant every scope-derived
    path helper relies on: project scope always carries a resolved project root
    (enforced by ``_resolve_scope`` and checked again in ``main``)."""

    assert project_root is not None, "project scope requires a project root"
    return project_root


def _lib_home(scope: str, project_root: Path | None) -> Path:
    if scope == "user":
        return Path.home() / ".orchflows" / "lib"
    return _require_project_root(project_root) / ".orchflows" / "lib"


def _scope_home(scope: str, project_root: Path | None) -> Path:
    if scope == "user":
        return Path.home() / ".orchflows"
    return _require_project_root(project_root) / ".orchflows"


def _bin_dir(scope: str, project_root: Path | None) -> Path:
    if scope == "user":
        return Path.home() / ".orchflows" / "bin"
    return _require_project_root(project_root) / ".orch" / "bin"


def _runtime_dirs(scope: str, project_root: Path | None) -> list[Path]:
    if scope == "user":
        return [Path.home() / ".orchflows" / "friction", Path.home() / ".orchflows" / "bin"]
    orch = _require_project_root(project_root) / ".orch"
    return [
        orch / "tickets",
        orch / "runs",
        orch / "friction",
        orch / "improvement" / "proposals",
        orch / "bin",
    ]


def _claude_scope_home(scope: str, project_root: Path | None) -> Path:
    if scope == "user":
        return Path.home() / ".claude"
    return _require_project_root(project_root) / ".claude"


def _claude_md_path(scope: str, project_root: Path | None) -> Path:
    if scope == "user":
        return Path.home() / ".claude" / "CLAUDE.md"
    return _require_project_root(project_root) / "CLAUDE.md"


def _claude_settings_path(scope: str, project_root: Path | None) -> Path:
    return _claude_scope_home(scope, project_root) / "settings.json"


def _claude_agents_dir(scope: str, project_root: Path | None) -> Path:
    return _claude_scope_home(scope, project_root) / "agents"


def _codex_user_home() -> Path:
    # Codex prompts have no project-local equivalent. Native role agents and
    # config use ``_codex_scope_home`` and therefore follow the selected scope.
    return Path.home() / ".codex"


def _codex_scope_home(scope: str, project_root: Path | None) -> Path:
    if scope == "user":
        return _codex_user_home()
    return _require_project_root(project_root) / ".codex"


def _codex_config_path(scope: str, project_root: Path | None) -> Path:
    return _codex_scope_home(scope, project_root) / "config.toml"


def _codex_agents_dir(scope: str, project_root: Path | None) -> Path:
    return _codex_scope_home(scope, project_root) / "agents"


def _codex_agents_path(scope: str, project_root: Path | None) -> Path:
    if scope == "user":
        return Path.home() / ".codex" / "AGENTS.md"
    return _require_project_root(project_root) / "AGENTS.md"


def _iter_json_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_json_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_json_strings(item)


def _codex_hooks_warnings(codex_home: Path) -> list[str]:
    """Preflight only: one-line warnings for ``hooks.json`` entries that look
    like a path to an orchflows file no longer present on disk. Never edits
    or deletes ``hooks.json`` — a dangling entry is the user's to fix."""

    hooks_path = codex_home / "hooks.json"
    if not hooks_path.is_file():
        return []
    try:
        data = json.loads(hooks_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    warnings = []
    seen = set()
    for value in _iter_json_strings(data):
        if "orch-" not in value or not any(sep in value for sep in ("/", "\\")):
            continue
        path = Path(value)
        if path.exists() or str(path) in seen:
            continue
        seen.add(str(path))
        warnings.append(f"warning: {hooks_path} references a missing orchflows path: {value}")
    return warnings


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


def _role_description(name: str, roles_path: Path) -> str:
    return f"Orchflows child role {name}; follow the role contract at {roles_path}."


def _role_instructions(name: str, roles_path: Path) -> str:
    return f"Read and follow the {name} contract in {roles_path} before acting. Stay within the delegated scope."


def render_codex_agent(name: str, profile: dict, roles_path: Path) -> str:
    binding = profile["codex"]
    lines = [
        f"name = {json.dumps(binding['agent_type'])}",
        f"description = {json.dumps(_role_description(name, roles_path))}",
        f"developer_instructions = {json.dumps(_role_instructions(name, roles_path))}",
        f"model = {json.dumps(binding['model'])}",
        f"model_reasoning_effort = {json.dumps(binding['model_reasoning_effort'])}",
    ]
    if binding.get("service_tier"):
        lines.append(f"service_tier = {json.dumps(binding['service_tier'])}")
    return "\n".join(lines) + "\n"


def render_claude_agent(name: str, profile: dict, roles_path: Path) -> str:
    binding = profile["claude"]
    lines = [
        "---",
        f"name: {name}",
        f"description: {json.dumps(_role_description(name, roles_path))}",
        f"model: {binding['model']}",
    ]
    if binding.get("effort"):
        lines.append(f"effort: {binding['effort']}")
    claude_transport = (
        " Write your contracted return into the dispatch's durable artifact, then "
        "deliver it or a pointer to it via SendMessage to your spawner as your final "
        "action - plain final text is not delivered to your caller."
    )
    lines.extend(["---", "", _role_instructions(name, roles_path) + claude_transport])
    return "\n".join(lines) + "\n"


# --- managed marker blocks ----------------------------------------------


def template_markers(template_text: str):
    lines = [line.strip() for line in template_text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("empty host-block template")
    return lines[0], lines[-1]


def resolved_python_interpreter() -> str:
    """The interpreter install.py verified itself running under (``sys.executable``);
    falls back to the bare command only when the platform cannot report one."""

    return sys.executable or "python"


def resolve_source_commit(repo_root: Path = REPO_ROOT) -> str | None:
    """The git HEAD commit of the repo this installer runs from, read directly
    from ``.git`` (no subprocess, no dependency on ``git`` being on PATH).
    Returns ``None`` whenever no ordinary ``.git`` checkout can be read —
    absent ``.git``, a worktree gitdir-file, a detached ref that resolves to
    nothing, or any I/O error."""

    head_file = repo_root / ".git" / "HEAD"
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
    ref_path = repo_root / ".git" / ref
    if ref_path.is_file():
        try:
            sha = ref_path.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        return sha or None
    packed_refs = repo_root / ".git" / "packed-refs"
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


def source_commit_drift_message(old_receipt: dict | None, new_commit: str | None) -> str | None:
    """``None`` unless both receipts name a commit and they differ — first
    installs and unavailable commits are not drift."""

    old_commit = (old_receipt or {}).get("source_commit")
    if old_commit and new_commit and old_commit != new_commit:
        return f"source commit drift: {old_commit} -> {new_commit}"
    return None


def render_host_block(
    template_text: str,
    bin_dir: PurePath,
    docs_dir: PurePath,
    skills_dir: PurePath,
    lib_dir: PurePath,
    python_interpreter: str,
) -> str:
    return (
        template_text.replace("{{ORCH_BIN}}", str(bin_dir))
        .replace("{{ORCH_DOCS}}", str(docs_dir))
        .replace("{{ORCH_SKILLS}}", str(skills_dir))
        .replace("{{ORCH_LIB}}", str(lib_dir))
        .replace("{{PYTHON}}", python_interpreter)
    )


def upsert_marked_block(text: str, block_text: str, start_marker: str, end_marker: str) -> str:
    if not block_text.endswith("\n"):
        block_text += "\n"
    if not text:
        return block_text
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == start_marker]
    ends = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == end_marker]
    if len(starts) > 1 or len(ends) > 1:
        raise ValueError(f"duplicate managed block markers in target file ({start_marker})")
    if len(starts) != len(ends):
        raise ValueError(f"unbalanced managed block markers in target file ({start_marker})")
    if not starts:
        if text.endswith("\n\n") or text.endswith("\r\n\r\n"):
            separator = ""
        elif text.endswith("\n") or text.endswith("\r\n"):
            separator = "\n"
        else:
            separator = "\n\n"
        return text + separator + block_text
    start_i, end_i = starts[0], ends[0]
    if start_i > end_i:
        raise ValueError(f"managed block markers are out of order in target file ({start_marker})")
    return "".join(lines[:start_i] + [block_text] + lines[end_i + 1 :])


def without_marked_block(text: str, start_marker: str, end_marker: str) -> str:
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == start_marker]
    ends = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == end_marker]
    if not starts and not ends:
        return text
    if len(starts) != 1 or len(ends) != 1 or starts[0] > ends[0]:
        raise ValueError(f"invalid managed block markers in target file ({start_marker})")
    return "".join(lines[: starts[0]] + lines[ends[0] + 1 :])


def upsert_import_line(text: str, import_line: str, legacy_start_marker: str, legacy_end_marker: str) -> tuple[str, str]:
    """Idempotently ensure ``import_line`` appears as its own line in ``text``,
    after stripping any legacy inline marker block left by an older install.
    Returns ``(updated_text, install_action)`` where ``install_action`` is one
    of ``created-file`` | ``migrated-from-block`` | ``added-import`` |
    ``already-present``."""

    existed = bool(text)
    had_legacy_block = legacy_start_marker in text and legacy_end_marker in text
    cleaned = without_marked_block(text, legacy_start_marker, legacy_end_marker)
    if any(line.rstrip("\r\n") == import_line for line in cleaned.splitlines()):
        return cleaned, "already-present"
    if not cleaned:
        updated = import_line + "\n"
    elif cleaned.endswith("\n\n") or cleaned.endswith("\r\n\r\n"):
        updated = cleaned + import_line + "\n"
    elif cleaned.endswith("\n") or cleaned.endswith("\r\n"):
        updated = cleaned + "\n" + import_line + "\n"
    else:
        updated = cleaned + "\n\n" + import_line + "\n"
    action = "migrated-from-block" if had_legacy_block else ("added-import" if existed else "created-file")
    return updated, action


def render_claude_settings(text: str) -> tuple[str, dict]:
    if text.strip():
        try:
            settings = json.loads(text)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid Claude settings JSON: {error}") from error
        if not isinstance(settings, dict):
            raise ValueError("Claude settings must be a JSON object")
    else:
        settings = {"$schema": CLAUDE_SETTINGS_SCHEMA}
    env = settings.setdefault("env", {})
    if not isinstance(env, dict):
        raise ValueError("Claude settings 'env' must be a JSON object")
    key = "CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY"
    previous = env.get(key)
    env[key] = str(CLAUDE_MAX_TOOL_USE_CONCURRENCY)
    details = {"setting": f"env.{key}", "previous": previous, "installed": env[key]}
    return json.dumps(settings, indent=2, ensure_ascii=False) + "\n", details


def render_codex_agent_limits(text: str) -> tuple[str, dict]:
    cleaned = without_marked_block(text, CODEX_LIMITS_START, CODEX_LIMITS_END)
    if tomllib is not None:
        try:
            parsed = tomllib.loads(cleaned)
        except tomllib.TOMLDecodeError as error:
            raise ValueError(f"invalid Codex config TOML: {error}") from error
    else:
        parsed = {}
    agents = parsed.get("agents", {}) if isinstance(parsed, dict) else {}
    previous = {
        "agents.max_threads": agents.get("max_threads") if isinstance(agents, dict) else None,
        "agents.max_depth": agents.get("max_depth") if isinstance(agents, dict) else None,
    }

    lines = cleaned.splitlines(keepends=True)
    agents_i = next((i for i, line in enumerate(lines) if _AGENTS_TABLE_RE.match(line.rstrip("\r\n"))), None)
    if agents_i is not None:
        section_end = next(
            (i for i in range(agents_i + 1, len(lines)) if _TOML_TABLE_RE.match(lines[i].rstrip("\r\n"))),
            len(lines),
        )
        section = [line for line in lines[agents_i + 1 : section_end] if not _AGENTS_LIMIT_RE.match(line)]
        block = [
            f"{CODEX_LIMITS_START}\n",
            f"max_threads = {CODEX_MAX_THREADS}\n",
            f"max_depth = {CODEX_MAX_DEPTH}\n",
            f"{CODEX_LIMITS_END}\n",
        ]
        updated = "".join(lines[: agents_i + 1] + block + section + lines[section_end:])
    else:
        first_table = next(
            (i for i, line in enumerate(lines) if _TOML_TABLE_RE.match(line.rstrip("\r\n"))), len(lines)
        )
        top_level = [line for line in lines[:first_table] if not _AGENTS_DOTTED_LIMIT_RE.match(line)]
        if top_level and top_level[-1].strip():
            top_level.append("\n")
        block = [
            f"{CODEX_LIMITS_START}\n",
            f"agents.max_threads = {CODEX_MAX_THREADS}\n",
            f"agents.max_depth = {CODEX_MAX_DEPTH}\n",
            f"{CODEX_LIMITS_END}\n",
        ]
        if first_table < len(lines):
            block.append("\n")
        updated = "".join(top_level + block + lines[first_table:])

    if tomllib is not None:
        try:
            tomllib.loads(updated)
        except tomllib.TOMLDecodeError as error:
            raise ValueError(f"could not merge Codex agent limits: {error}") from error
    details = {
        "settings": {
            "agents.max_threads": CODEX_MAX_THREADS,
            "agents.max_depth": CODEX_MAX_DEPTH,
        },
        "previous": previous,
    }
    return updated, details


# --- plan -----------------------------------------------------------------


@dataclass
class BlockPlan:
    dest: Path
    content: str
    start_marker: str
    end_marker: str
    label: str


@dataclass
class ConfigPlan:
    dest: Path
    content: str
    kind: str
    label: str
    details: dict = field(default_factory=dict)


@dataclass
class ImportPlan:
    dest: Path
    import_target: Path
    legacy_start_marker: str
    legacy_end_marker: str
    label: str


@dataclass
class Plan:
    scope: str
    project_root: Path | None
    lib_home: Path
    scope_home: Path
    bin_dir: Path
    receipt_path: Path
    runtime_dirs: list = field(default_factory=list)
    lib_copies: list = field(default_factory=list)       # (src, dest)
    scripts: list = field(default_factory=list)          # (src, dest)
    claude_adapters: list = field(default_factory=list)  # (dest, content) — per-skill SKILL.md stubs
    codex_prompts: list = field(default_factory=list)    # (dest, content)
    codex_skills: list = field(default_factory=list)     # (dest, content) — redirect stubs
    by_name: list = field(default_factory=list)          # (dest, content) — flat name->tiered-source pointers, host-agnostic
    claude_agents: list = field(default_factory=list)    # (dest, content)
    codex_agents: list = field(default_factory=list)     # (dest, content)
    configs: list = field(default_factory=list)          # ConfigPlan
    blocks: list = field(default_factory=list)           # BlockPlan — inline marker blocks
    host_block: ConfigPlan | None = None                 # ~/.orchflows/host-block.md, user scope only
    claude_import: ImportPlan | None = None              # CLAUDE.md import line, user scope only
    warnings: list = field(default_factory=list)         # preflight, informational only
    manage_host_surfaces: bool = True                    # False for thin project plans
    claude_enabled: bool = True                          # user scope: ~/.claude was detected
    codex_enabled: bool = True                           # user scope: ~/.codex was detected


_BUILD_ARTIFACT_SUFFIXES = (".pyc", ".pyo")
_BUILD_ARTIFACT_DIR_NAMES = ("__pycache__",)


def _is_build_artifact(path: Path) -> bool:
    """Stray local bytecode/cache files are never canonical library content."""

    if path.suffix in _BUILD_ARTIFACT_SUFFIXES:
        return True
    return any(part in _BUILD_ARTIFACT_DIR_NAMES for part in path.parts)


def _host_block_content() -> tuple[str, str, str]:
    """Render the instruction block against the *user* library paths
    (``~/.orchflows/...``). Both scopes point here: project installs carry
    no library of their own and read the user install instead."""

    lib_home = _lib_home("user", None)
    bin_dir = _bin_dir("user", None)
    template_text = HOST_BLOCK_TEMPLATE.read_text(encoding="utf-8")
    start_marker, end_marker = template_markers(template_text)
    content = render_host_block(
        template_text, bin_dir, lib_home / "docs", lib_home / "skills", lib_home, resolved_python_interpreter()
    )
    return content, start_marker, end_marker


def _build_project_plan(project_root: Path) -> Plan:
    """Thin stub: only the two managed instruction blocks plus a minimal
    receipt. No lib copy, no runtime dirs, no ``.claude``/``.codex`` writes —
    a project install borrows the user install for everything else."""

    host_block, start_marker, end_marker = _host_block_content()
    blocks = [
        BlockPlan(
            _claude_md_path("project", project_root),
            host_block,
            start_marker,
            end_marker,
            "Claude Code instruction block",
        ),
        BlockPlan(
            _codex_agents_path("project", project_root),
            host_block,
            start_marker,
            end_marker,
            "Codex AGENTS.md instruction block",
        ),
    ]
    scope_home = _scope_home("project", project_root)
    return Plan(
        scope="project",
        project_root=project_root,
        lib_home=_lib_home("project", project_root),
        scope_home=scope_home,
        bin_dir=_bin_dir("project", project_root),
        blocks=blocks,
        receipt_path=scope_home / "receipt.json",
        manage_host_surfaces=False,
    )


def detect_hosts(home: Path | None = None) -> tuple[bool, bool]:
    """(claude_enabled, codex_enabled) from whether ``~/.claude`` and
    ``~/.codex`` exist. Presence of the directory is the whole signal — not
    whether a CLI binary happens to be on PATH."""

    home = home if home is not None else Path.home()
    return (home / ".claude").is_dir(), (home / ".codex").is_dir()


def _build_user_plan() -> Plan:
    lib_home = _lib_home("user", None)
    scope_home = _scope_home("user", None)
    bin_dir = _bin_dir("user", None)
    home = Path.home()
    claude_enabled, codex_enabled = detect_hosts(home)
    if not claude_enabled and not codex_enabled:
        raise ValueError(
            "neither ~/.claude nor ~/.codex was found; install Claude Code or the "
            "Codex CLI first, then rerun this installer."
        )

    lib_copies = []
    for name in CANONICAL_DIRS:
        src_dir = REPO_ROOT / name
        if not src_dir.is_dir():
            continue
        for path in sorted(src_dir.rglob("*")):
            if path.is_file() and not _is_build_artifact(path):
                rel = path.relative_to(REPO_ROOT)
                lib_copies.append((path, lib_home / rel))

    scripts = [(REPO_ROOT / "scripts" / name, bin_dir / name) for name in SCRIPT_NAMES]

    claude_scope_home = _claude_scope_home("user", None)
    codex_user_home = _codex_user_home()
    claude_adapters = []
    codex_prompts = []
    codex_skills = []
    by_name = []
    for skill_md in discover_packages():
        rel = skill_md.relative_to(REPO_ROOT)
        name = skill_md.parent.name
        text = skill_md.read_text(encoding="utf-8")
        frontmatter, body = split_frontmatter(text)
        description = frontmatter_field(frontmatter, "description") or ""
        lib_skill_md = (lib_home / rel).resolve()
        # Flat, host-agnostic resolution: one deterministic path per canonical
        # name, tier or pack alike, so no agent has to guess a sublayer. The
        # stub only points at the tiered source (never duplicates it), so it
        # carries no relative links to break.
        by_name.append(
            (
                lib_home / "by-name" / name / "SKILL.md",
                frontmatter + f"\nRead {lib_skill_md} and follow it exactly.\n",
            )
        )
        if claude_enabled:
            claude_adapters.append(
                (claude_scope_home / "skills" / name / "SKILL.md", host_legal_frontmatter(frontmatter) + f"@{lib_skill_md}\n")
            )
        if codex_enabled:
            codex_prompts.append(
                (codex_user_home / "prompts" / f"{name}.md", f"# {description}\n\n{body.strip()}\n")
            )
            if name in CODEX_SKILL_REDIRECT_NAMES:
                codex_skills.append(
                    (
                        codex_user_home / "skills" / name / "SKILL.md",
                        frontmatter + f"\nRead {lib_skill_md} and follow it exactly.\n",
                    )
                )

    roles_path = (lib_home / "rules" / "roles.md").resolve()
    profiles = load_role_profiles()
    claude_agents = []
    codex_agents = []
    for name in (f"orch-{role}" for role in PROFILE_ROLES):
        profile = profiles[name]
        if claude_enabled:
            claude_agents.append(
                (_claude_agents_dir("user", None) / f"{name}.md", render_claude_agent(name, profile, roles_path))
            )
        if codex_enabled:
            codex_agent_type = profile["codex"]["agent_type"]
            codex_agents.append(
                (
                    _codex_agents_dir("user", None) / f"{codex_agent_type}.toml",
                    render_codex_agent(name, profile, roles_path),
                )
            )

    configs = []
    if claude_enabled:
        claude_settings_path = _claude_settings_path("user", None)
        claude_settings_text = (
            claude_settings_path.read_text(encoding="utf-8") if claude_settings_path.is_file() else ""
        )
        claude_settings, claude_details = render_claude_settings(claude_settings_text)
        configs.append(
            ConfigPlan(
                claude_settings_path,
                claude_settings,
                "claude-config",
                "Claude Code concurrency settings",
                claude_details,
            )
        )
    if codex_enabled:
        codex_config_path = _codex_config_path("user", None)
        codex_config_text = codex_config_path.read_text(encoding="utf-8") if codex_config_path.is_file() else ""
        codex_config, codex_details = render_codex_agent_limits(codex_config_text)
        configs.append(
            ConfigPlan(
                codex_config_path,
                codex_config,
                "codex-config",
                "Codex agent limits",
                codex_details,
            )
        )

    host_block, start_marker, end_marker = _host_block_content()
    blocks = []
    host_block_plan = None
    claude_import_plan = None
    if claude_enabled:
        host_block_path = scope_home / "host-block.md"
        host_block_plan = ConfigPlan(host_block_path, host_block, "host-block", "Host instruction block")
        claude_import_plan = ImportPlan(
            _claude_md_path("user", None),
            host_block_path.resolve(),
            start_marker,
            end_marker,
            "Claude Code instruction import",
        )
    if codex_enabled:
        blocks.append(
            BlockPlan(
                _codex_agents_path("user", None),
                host_block,
                start_marker,
                end_marker,
                "Codex AGENTS.md instruction block",
            )
        )

    return Plan(
        scope="user",
        project_root=None,
        lib_home=lib_home,
        scope_home=scope_home,
        bin_dir=bin_dir,
        runtime_dirs=_runtime_dirs("user", None),
        lib_copies=lib_copies,
        scripts=scripts,
        claude_adapters=claude_adapters,
        codex_prompts=codex_prompts,
        codex_skills=codex_skills,
        by_name=by_name,
        claude_agents=claude_agents,
        codex_agents=codex_agents,
        configs=configs,
        blocks=blocks,
        host_block=host_block_plan,
        claude_import=claude_import_plan,
        receipt_path=scope_home / "receipt.json",
        warnings=_codex_hooks_warnings(codex_user_home) if codex_enabled else [],
        claude_enabled=claude_enabled,
        codex_enabled=codex_enabled,
    )


def build_plan(scope: str, project_root: Path | None) -> Plan:
    if scope == "project":
        return _build_project_plan(_require_project_root(project_root))
    return _build_user_plan()


def print_plan(plan: Plan) -> None:
    print(f"scope: {plan.scope}")
    if plan.project_root is not None:
        print(f"project root: {plan.project_root}")
    if plan.scope == "user":
        print(f"detected Claude Code (~/.claude): {'yes' if plan.claude_enabled else 'no'}")
        print(f"detected Codex (~/.codex): {'yes' if plan.codex_enabled else 'no'}")
    print(f"source commit: {resolve_source_commit() or 'unknown'}")
    print(f"library home: {plan.lib_home}")
    print(f"bin dir: {plan.bin_dir}")
    print()
    print(f"runtime directories ({len(plan.runtime_dirs)}):")
    for directory in plan.runtime_dirs:
        print(f"  mkdir: {directory}")
    print()
    print(f"library files ({len(plan.lib_copies)}):")
    for pair in plan.lib_copies:
        print(f"  copy: {pair[1]}")
    print()
    print(f"flat name index ({len(plan.by_name)}):")
    for pair in plan.by_name:
        print(f"  write: {pair[0]}")
    print()
    print(f"scripts ({len(plan.scripts)}):")
    for pair in plan.scripts:
        print(f"  install: {pair[1]}")
    print()
    print(f"Claude Code skill adapters ({len(plan.claude_adapters)}):")
    for pair in plan.claude_adapters:
        print(f"  write: {pair[0]}")
    print()
    print(f"Codex prompts ({len(plan.codex_prompts)}):")
    for pair in plan.codex_prompts:
        print(f"  write: {pair[0]}")
    print()
    print(f"Codex redirect skills ({len(plan.codex_skills)}):")
    for pair in plan.codex_skills:
        print(f"  write: {pair[0]}")
    print()
    print(f"Claude Code role agents ({len(plan.claude_agents)}):")
    for pair in plan.claude_agents:
        print(f"  write: {pair[0]}")
    print()
    print(f"Codex role agents ({len(plan.codex_agents)}):")
    for pair in plan.codex_agents:
        print(f"  write: {pair[0]}")
    print()
    print(f"host configuration files ({len(plan.configs)}):")
    for config in plan.configs:
        print(f"  {config.label}: {config.dest}")
    print()
    if plan.host_block is not None:
        print(f"host instruction file: {plan.host_block.dest}")
        print()
    print(f"managed blocks ({len(plan.blocks)}):")
    for block in plan.blocks:
        print(f"  {block.label}: {block.dest}")
    print()
    if plan.claude_import is not None:
        print("managed imports (1):")
        print(f"  {plan.claude_import.label}: {plan.claude_import.dest} -> @{plan.claude_import.import_target}")
        print()
    print(f"receipt: {plan.receipt_path}")


# --- apply -----------------------------------------------------------------


def _load_json(path: Path):
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _installed_file(path: Path, kind: str, action: str, details: dict | None = None) -> dict:
    entry = {
        "path": str(path),
        "kind": kind,
        "install_action": action,
        "sha256": _sha256_file(path),
    }
    if details:
        entry["details"] = details
    return entry


def _prune_empty_dirs(path: Path, boundary: Path) -> None:
    """Remove ``path`` and empty ancestors, stopping at (and never removing) boundary."""

    try:
        boundary_resolved = boundary.resolve()
    except OSError:
        return
    try:
        current = path.resolve()
    except OSError:
        return
    while current != boundary_resolved and boundary_resolved in current.parents:
        try:
            if not current.is_dir() or any(current.iterdir()):
                return
            current.rmdir()
        except OSError:
            return
        current = current.parent


def _remove_stale(old_receipt, kind: str, keep_paths: set, boundary: Path) -> None:
    if not old_receipt:
        return
    for entry in old_receipt.get("files", []):
        if entry.get("kind") != kind:
            continue
        path = Path(entry["path"])
        if str(path) in keep_paths:
            continue
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            continue
        _prune_empty_dirs(path.parent, boundary)


def _preflight_role_agents(plan: Plan, old_receipt: dict | None) -> None:
    """Refuse to replace native role profiles not owned by an unchanged receipt."""

    old_entries = {
        (entry.get("path"), entry.get("kind")): entry
        for entry in (old_receipt or {}).get("files", [])
    }
    conflicts = []
    for kind, files in (
        ("claude-agent", plan.claude_agents),
        ("codex-agent", plan.codex_agents),
    ):
        for path, desired in files:
            if not path.exists() and not path.is_symlink():
                continue
            if not path.is_file() or path.is_symlink():
                conflicts.append(f"{path} (not a regular file)")
                continue
            current = path.read_text(encoding="utf-8")
            if current == desired:
                continue
            old_entry = old_entries.get((str(path), kind))
            recorded_hash = old_entry.get("sha256") if old_entry else None
            if not recorded_hash:
                conflicts.append(f"{path} (not owned by this install receipt)")
                continue
            if _sha256_file(path) != recorded_hash:
                conflicts.append(f"{path} (changed since the recorded install)")

    if conflicts:
        rendered = "\n  ".join(conflicts)
        raise FileExistsError(
            "refusing to overwrite native role profile(s):\n  "
            f"{rendered}\nMove or remove the conflicting files, then reinstall."
        )


def apply_plan(plan: Plan) -> dict:
    old_receipt = _load_json(plan.receipt_path)
    _preflight_role_agents(plan, old_receipt)
    old_entries = {
        (entry.get("path"), entry.get("kind")): entry
        for entry in (old_receipt or {}).get("files", [])
    }

    def install_action(path: Path, kind: str, existed: bool) -> str:
        old_entry = old_entries.get((str(path), kind), {})
        return old_entry.get("install_action") or ("replaced" if existed else "created")

    def install_details(path: Path, kind: str, details: dict) -> dict:
        old_entry = old_entries.get((str(path), kind), {})
        return old_entry.get("details") or details

    # Library tree: fully installer-owned, replaced wholesale. Thin project
    # plans carry no lib_copies and never touch a project's ``.orchflows/lib``.
    old_lib_files = set()
    if plan.lib_copies:
        if plan.lib_home.exists():
            old_lib_files = {str(path.resolve()) for path in plan.lib_home.rglob("*") if path.is_file()}
            shutil.rmtree(plan.lib_home)
        for src, dest in plan.lib_copies:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

    for directory in plan.runtime_dirs:
        directory.mkdir(parents=True, exist_ok=True)

    written_files = []

    # Everything below writes into ``.claude``/``.codex`` (adapters, prompts,
    # redirect skills, role agents, host configs). Thin project plans set
    # ``manage_host_surfaces`` False and skip all of it — no writes, no
    # receipt-driven removals — so reinstalling over a project never touches
    # a legacy fat project install's ``.claude``/``.codex`` files.
    if plan.manage_host_surfaces:
        for src, dest in plan.scripts:
            action = install_action(dest, "script", dest.is_file())
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            written_files.append(_installed_file(dest, "script", action))

        claude_scope_home = _claude_scope_home(plan.scope, plan.project_root)
        _remove_stale(
            old_receipt, "adapter", {str(dest) for dest, _ in plan.claude_adapters}, claude_scope_home / "skills"
        )
        for dest, content in plan.claude_adapters:
            action = install_action(dest, "adapter", dest.is_file())
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            written_files.append(_installed_file(dest, "adapter", action))

        codex_prompts_dir = _codex_user_home() / "prompts"
        _remove_stale(old_receipt, "prompt", {str(dest) for dest, _ in plan.codex_prompts}, codex_prompts_dir)
        for dest, content in plan.codex_prompts:
            action = install_action(dest, "prompt", dest.is_file())
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            written_files.append(_installed_file(dest, "prompt", action))

        codex_skills_dir = _codex_user_home() / "skills"
        _remove_stale(old_receipt, "codex-skill", {str(dest) for dest, _ in plan.codex_skills}, codex_skills_dir)
        for dest, content in plan.codex_skills:
            action = install_action(dest, "codex-skill", dest.is_file())
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            written_files.append(_installed_file(dest, "codex-skill", action))

        for kind, files, boundary in (
            ("claude-agent", plan.claude_agents, _claude_agents_dir(plan.scope, plan.project_root)),
            ("codex-agent", plan.codex_agents, _codex_agents_dir(plan.scope, plan.project_root)),
        ):
            _remove_stale(old_receipt, kind, {str(dest) for dest, _ in files}, boundary)
            for dest, content in files:
                action = install_action(dest, kind, dest.is_file())
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")
                written_files.append(_installed_file(dest, kind, action))

        for config in plan.configs:
            action = install_action(config.dest, config.kind, config.dest.is_file())
            details = install_details(config.dest, config.kind, config.details)
            config.dest.parent.mkdir(parents=True, exist_ok=True)
            config.dest.write_text(config.content, encoding="utf-8")
            written_files.append(_installed_file(config.dest, config.kind, action, details))

        if plan.host_block is not None:
            host_block = plan.host_block
            action = install_action(host_block.dest, host_block.kind, host_block.dest.is_file())
            host_block.dest.parent.mkdir(parents=True, exist_ok=True)
            host_block.dest.write_text(host_block.content, encoding="utf-8")
            written_files.append(_installed_file(host_block.dest, host_block.kind, action))

    for _, dest in plan.lib_copies:
        action = install_action(dest, "lib", str(dest.resolve()) in old_lib_files)
        written_files.append(_installed_file(dest, "lib", action))

    # Flat name index: host-agnostic pointers under ``lib_home/by-name``. Lives
    # inside the wholesale-replaced library tree, so the rmtree above already
    # cleared any prior generation — no per-file stale sweep is needed.
    for dest, content in plan.by_name:
        existed = dest.is_file()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        written_files.append(_installed_file(dest, "by-name", install_action(dest, "by-name", existed)))

    written_blocks = []
    for block in plan.blocks:
        existed = block.dest.is_file()
        block.dest.parent.mkdir(parents=True, exist_ok=True)
        current_text = block.dest.read_text(encoding="utf-8") if existed else ""
        had_block = block.start_marker in current_text and block.end_marker in current_text
        action = "updated-block" if had_block else ("added-block" if existed else "created-file")
        updated = upsert_marked_block(current_text, block.content, block.start_marker, block.end_marker)
        block.dest.write_text(updated, encoding="utf-8")
        written_blocks.append(
            {
                "path": str(block.dest),
                "start_marker": block.start_marker,
                "end_marker": block.end_marker,
                "install_action": action,
            }
        )

    written_imports = []
    if plan.claude_import is not None:
        imp = plan.claude_import
        imp.dest.parent.mkdir(parents=True, exist_ok=True)
        current_text = imp.dest.read_text(encoding="utf-8") if imp.dest.is_file() else ""
        import_line = f"@{imp.import_target}"
        updated, action = upsert_import_line(current_text, import_line, imp.legacy_start_marker, imp.legacy_end_marker)
        imp.dest.write_text(updated, encoding="utf-8")
        written_imports.append(
            {
                "path": str(imp.dest),
                "import_line": import_line,
                "install_action": action,
            }
        )

    extra_dirs = []
    if plan.scripts:
        extra_dirs.append(str(plan.bin_dir))
    if plan.lib_copies:
        extra_dirs.append(str(plan.lib_home))
    if plan.claude_agents:
        extra_dirs.append(str(_claude_agents_dir(plan.scope, plan.project_root)))
    if plan.codex_agents:
        extra_dirs.append(str(_codex_agents_dir(plan.scope, plan.project_root)))

    receipt = {
        "version": 4,
        "scope": plan.scope,
        "project_root": str(plan.project_root) if plan.project_root is not None else None,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_commit": resolve_source_commit(),
        "lib_home": str(plan.lib_home),
        "bin_dir": str(plan.bin_dir),
        "files": written_files,
        "blocks": written_blocks,
        "imports": written_imports,
        "dirs": list(dict.fromkeys([str(d) for d in plan.runtime_dirs] + extra_dirs)),
    }
    plan.receipt_path.parent.mkdir(parents=True, exist_ok=True)
    plan.receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return receipt


def print_summary(plan: Plan) -> None:
    print(f"Installed orchflows at {plan.scope} scope.")
    if not plan.manage_host_surfaces:
        print(f"  instruction blocks: {len(plan.blocks)} written")
        for block in plan.blocks:
            print(f"    {block.label}: {block.dest}")
        print(f"  receipt:     {plan.receipt_path}")
        return
    if plan.scope == "user":
        print(f"  detected Claude Code (~/.claude): {'yes' if plan.claude_enabled else 'no'}")
        print(f"  detected Codex (~/.codex): {'yes' if plan.codex_enabled else 'no'}")
    print(f"  library:     {plan.lib_home}  ({len(plan.lib_copies)} files)")
    if plan.by_name:
        print(f"  flat index:  {plan.lib_home / 'by-name'}  ({len(plan.by_name)} names)")
    print(f"  scripts:     {plan.bin_dir}")
    if plan.claude_enabled:
        host_block_dest = plan.host_block.dest if plan.host_block is not None else "(none)"
        print(
            f"  Claude Code: {len(plan.claude_adapters)} skill adapter(s), {len(plan.claude_agents)} role agent(s); "
            f"import in {_claude_md_path(plan.scope, plan.project_root)} -> {host_block_dest}; "
            f"settings in {_claude_settings_path(plan.scope, plan.project_root)}"
        )
    if plan.codex_enabled:
        print(
            f"  Codex:       {len(plan.codex_prompts)} prompt(s), {len(plan.codex_skills)} redirect skill(s), "
            f"{len(plan.codex_agents)} role agent(s); "
            f"instruction block in {_codex_agents_path(plan.scope, plan.project_root)}; "
            f"settings in {_codex_config_path(plan.scope, plan.project_root)}"
        )
    print(f"  receipt:     {plan.receipt_path}")


# --- uninstall ---------------------------------------------------------


def _uninstall_boundary(path: Path, scope: str, project_root: Path | None) -> Path:
    """Codex prompts live under the user home even for project installs."""

    if scope == "project":
        root = _require_project_root(project_root)
        try:
            path.resolve().relative_to(root.resolve())
            return root
        except (OSError, ValueError):
            pass
    return Path.home()


def _auto_remove_path_is_safe(
    path: Path, kind: str, scope: str, project_root: Path | None
) -> bool:
    if kind == "adapter":
        boundary = _claude_scope_home(scope, project_root) / "skills"
    elif kind == "codex-skill":
        boundary = _codex_user_home() / "skills"
    else:
        boundary = _codex_user_home() / "prompts"
    scope_boundary = (
        _require_project_root(project_root)
        if kind == "adapter" and scope == "project"
        else Path.home()
    )
    try:
        path.absolute().relative_to(boundary.absolute())
        boundary.resolve().relative_to(scope_boundary.resolve())
        path.resolve().relative_to(boundary.resolve())
    except (OSError, ValueError):
        return False
    return not path.is_symlink()


def run_uninstall(scope: str, project_root: Path | None, dry_run: bool) -> dict:
    scope_home = _scope_home(scope, project_root)
    receipt_path = scope_home / "receipt.json"
    receipt = _load_json(receipt_path)
    if receipt is None:
        return {
            "skill_actions": [],
            "manual_actions": [],
            "note": f"no valid receipt found at {receipt_path}",
        }

    skill_actions = []
    manual_actions = []
    for entry in receipt.get("files", []):
        path = Path(entry["path"])
        kind = entry.get("kind", "unknown")
        install_action = entry.get("install_action", "unknown")
        if kind not in AUTO_REMOVE_KINDS:
            details = entry.get("details")
            detail_suffix = (
                f"; installer details {json.dumps(details, ensure_ascii=False, sort_keys=True)}"
                if details
                else ""
            )
            if install_action == "created":
                action = f"delete installer-created {kind} file manually{detail_suffix}"
            elif install_action == "replaced":
                action = (
                    f"review installer-replaced {kind} file; no original backup was recorded{detail_suffix}"
                )
            else:
                action = f"review {kind} file; install action is unknown{detail_suffix}"
            manual_actions.append(
                {
                    "path": str(path),
                    "action": action,
                }
            )
            continue

        if not _auto_remove_path_is_safe(path, kind, scope, project_root):
            manual_actions.append(
                {
                    "path": str(path),
                    "action": "review skill file; path is outside its verified install boundary; not removed",
                }
            )
            continue

        if not path.is_file():
            skill_actions.append({"path": str(path), "action": "already absent"})
            continue

        if install_action != "created":
            manual_actions.append(
                {
                    "path": str(path),
                    "action": (
                        "review installer-replaced skill file; no original backup was recorded; not removed"
                        if install_action == "replaced"
                        else "review skill file; install action is unknown; not removed"
                    ),
                }
            )
            continue

        installed_hash = entry.get("sha256")
        try:
            current_hash = _sha256_file(path)
        except OSError as error:
            manual_actions.append(
                {"path": str(path), "action": f"review skill file; could not verify: {error}"}
            )
            continue

        if not installed_hash or current_hash != installed_hash:
            reason = "no install hash" if not installed_hash else "modified since install"
            manual_actions.append(
                {"path": str(path), "action": f"review skill file; {reason}; not removed"}
            )
            continue

        if dry_run:
            skill_actions.append({"path": str(path), "action": "would remove unchanged skill"})
            continue
        try:
            path.unlink()
        except OSError as error:
            manual_actions.append(
                {"path": str(path), "action": f"remove skill file manually; automatic removal failed: {error}"}
            )
            continue
        _prune_empty_dirs(path.parent, _uninstall_boundary(path, scope, project_root))
        skill_actions.append({"path": str(path), "action": "removed unchanged skill"})

    for entry in receipt.get("blocks", []):
        manual_actions.append(
            {
                "path": entry["path"],
                "action": (
                    f"remove managed block {entry['start_marker']!r} through {entry['end_marker']!r}; "
                    f"installer {entry.get('install_action', 'unknown')}; not changed"
                ),
            }
        )

    for entry in receipt.get("imports", []):
        manual_actions.append(
            {
                "path": entry["path"],
                "action": (
                    f"remove managed import line {entry['import_line']!r}; "
                    f"installer {entry.get('install_action', 'unknown')}; not changed"
                ),
            }
        )

    for dir_str in receipt.get("dirs", []):
        manual_actions.append({"path": dir_str, "action": "remove directory manually when empty"})

    manual_actions.append(
        {"path": str(receipt_path), "action": "delete receipt after completing manual cleanup"}
    )
    return {
        "skill_actions": skill_actions,
        "manual_actions": manual_actions,
        "receipt": str(receipt_path),
    }


# --- CLI -----------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install or remove orchflows for Claude Code and Codex.")
    parser.add_argument("--user", action="store_true", help="Install scope: user (all sessions).")
    parser.add_argument(
        "--project",
        nargs="?",
        const=".",
        default=None,
        metavar="PATH",
        help="Install scope: project, optionally at PATH (default: current directory).",
    )
    parser.add_argument("--yes", action="store_true", help="Skip the interactive scope prompt (defaults to user).")
    parser.add_argument("--dry-run", action="store_true", help="Print the full plan; write nothing.")
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove unchanged generated skills and print receipt-based manual cleanup.",
    )
    return parser


def _prompt_scope() -> str:
    print("Install scope? [1] user (all sessions)  [2] project (this repo only)")
    print("Project scope must be run in each project repository.")
    try:
        choice = input("> ").strip()
    except EOFError:
        choice = ""
    return "project" if choice == "2" else "user"


def _resolve_scope(args) -> tuple[str, Path | None]:
    if args.user and args.project is not None:
        raise SystemExit("error: --user and --project are mutually exclusive")
    if args.uninstall and not args.user and args.project is None:
        raise SystemExit("error: --uninstall requires --user or --project [PATH]")
    if args.user:
        return "user", None
    if args.project is not None:
        return "project", Path(args.project).resolve()
    if args.dry_run or args.yes:
        return "user", None
    return ("project", Path.cwd().resolve()) if _prompt_scope() == "project" else ("user", None)


def main(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    try:
        scope, project_root = _resolve_scope(args)
    except SystemExit as error:
        print(error, file=sys.stderr)
        return 2

    if scope == "project" and not _require_project_root(project_root).is_dir():
        print(f"error: project root does not exist: {project_root}", file=sys.stderr)
        return 1

    if args.uninstall:
        try:
            result = run_uninstall(scope, project_root, args.dry_run)
        except Exception as error:
            print(f"error: uninstall failed: {error}", file=sys.stderr)
            return 1
        print(f"skill actions ({len(result['skill_actions'])}):")
        for entry in result["skill_actions"]:
            print(f"  {entry['action']}: {entry['path']}")
        print(f"manual cleanup required ({len(result['manual_actions'])}):")
        for entry in result["manual_actions"]:
            print(f"  {entry['action']}: {entry['path']}")
        if "receipt" in result:
            print(f"receipt retained: {result['receipt']}")
        if "note" in result:
            print(result["note"])
        return 0

    try:
        plan = build_plan(scope, project_root)
    except Exception as error:
        print(f"error: could not build install plan: {error}", file=sys.stderr)
        return 1

    for warning in plan.warnings:
        print(warning)

    if args.dry_run:
        print_plan(plan)
        return 0

    old_receipt = _load_json(plan.receipt_path)
    try:
        receipt = apply_plan(plan)
    except Exception as error:
        print(f"error: install failed: {error}", file=sys.stderr)
        return 1

    drift = source_commit_drift_message(old_receipt, receipt.get("source_commit"))
    if drift:
        print(drift)

    print_summary(plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
