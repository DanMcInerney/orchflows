"""Conservative receipt-driven uninstall planning and application."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, NamedTuple

from scripts import orchflows_home

from .application import _load_json, _prune_empty_dirs, _sha256_file
from .foundation import (
    AUTO_REMOVE_KINDS,
    _HOST_ADAPTERS,
    _claude_agents_dir,
    _claude_user_home,
    _codex_agents_dir,
    _codex_user_home,
    _frontend_home,
    _grok_agents_dir,
    _grok_rules_path,
    _grok_skills_dir,
    _grok_user_home,
    _scope_home,
)
from .hosts import host_item_path
from .managed_text import without_codex_agent_limits, without_grok_subagent_limits

# --- legacy project paths ----------------------------------------------
#
# Installation writes one scope, the user's. A receipt written by an older
# version that installed into a project tree is still cleaned up, so the
# project half of every path this cleanup reads lives here -- reachable from
# ``--project PATH --uninstall`` and from nowhere else.


def _require_project_root(project_root: Path | None) -> Path:
    """Narrow ``Path | None`` to ``Path`` at the invariant ``--project``
    enforces: project cleanup always carries a resolved project root."""

    assert project_root is not None, "project cleanup requires a project root"
    return project_root


def _uninstall_home(scope: str, project_root: Path | None) -> Path:
    if scope == "project":
        return _require_project_root(project_root) / ".orchflows"
    return _scope_home()


def _claude_home(scope: str, project_root: Path | None) -> Path:
    if scope == "project":
        return _require_project_root(project_root) / ".claude"
    return _claude_user_home()


def _codex_home(scope: str, project_root: Path | None) -> Path:
    if scope == "project":
        return _require_project_root(project_root) / ".codex"
    return _codex_user_home()


def _claude_agents(scope: str, project_root: Path | None) -> Path:
    if scope == "project":
        return host_item_path(
            "claude", "role_agent", _claude_home(scope, project_root),
            _HOST_ADAPTERS, profile="{profile}",
        ).parent
    return _claude_agents_dir()


def _codex_agents(scope: str, project_root: Path | None) -> Path:
    if scope == "project":
        return host_item_path(
            "codex", "role_agent", _codex_home(scope, project_root),
            _HOST_ADAPTERS, agent_type="{agent_type}",
        ).parent
    return _codex_agents_dir()


# --- uninstall ---------------------------------------------------------


def _claude_root(scope: str, project_root: Path | None) -> Path:
    return _require_project_root(project_root) if scope == "project" else _claude_user_home()


def _codex_root(scope: str, project_root: Path | None) -> Path:
    return _require_project_root(project_root) if scope == "project" else _codex_user_home()


# Where each auto-removable kind must be found for its receipt entry to be
# honoured: the directory the installer puts that kind in, and the host root
# that directory must itself sit inside. Both are recomputed from the scope
# rather than read off the receipt, so an entry naming a path outside them is
# refused instead of obeyed. A kind absent here is never removed
# automatically, whatever the receipt claims -- and the keys are held equal to
# ``AUTO_REMOVE_KINDS`` by a check rather than by a reader's memory, so a kind
# widened onto that set without a boundary fails loudly instead of silently
# falling through to some other host's directory.
_AUTO_REMOVE_BOUNDARIES = {
    "adapter": lambda scope, root: (
        _claude_home(scope, root) / "skills", _claude_root(scope, root)
    ),
    "claude-agent": lambda scope, root: (
        _claude_agents(scope, root), _claude_root(scope, root)
    ),
    "codex-agent": lambda scope, root: (
        _codex_agents(scope, root), _codex_root(scope, root)
    ),
    "prompt": lambda scope, root: (_codex_user_home() / "prompts", _codex_user_home()),
    "codex-skill": lambda scope, root: (_codex_user_home() / "skills", _codex_user_home()),
    "codex-config": lambda scope, root: (_codex_user_home(), _codex_user_home()),
    "frontend-asset": lambda scope, root: (_frontend_home(), _frontend_home().parent),
    "grok-skill": lambda scope, root: (_grok_skills_dir(), _grok_user_home()),
    "grok-agent": lambda scope, root: (_grok_agents_dir(), _grok_user_home()),
    "grok-rules": lambda scope, root: (_grok_rules_path().parent, _grok_user_home()),
    "grok-config": lambda scope, root: (_grok_user_home(), _grok_user_home()),
}

# What the report calls the thing it removed, and what a review line calls
# the same thing. Defaulting to the skill wording keeps every Claude and
# Codex line exactly as it was.
_DEFAULT_NOUNS = ("skill", "skill file")
_REMOVAL_NOUNS = {
    "frontend-asset": ("frontend asset", "frontend asset"),
    "claude-agent": ("Claude role agent", "Claude role agent file"),
    "codex-agent": ("Codex role agent", "Codex role agent file"),
    "grok-skill": ("Grok skill", "Grok skill file"),
    "grok-agent": ("Grok role agent", "Grok role agent file"),
    "grok-rules": ("Grok instruction file", "Grok instruction file"),
    "grok-config": ("Grok config", "Grok config"),
}


class _LimitRemoval(NamedTuple):
    """How one host's managed limit block comes back out of its own config.

    Only the transform and the two nouns differ between the hosts, so the
    arm below has one owner. Nothing about the hazard is one host's: both
    files are written by the host's own CLI as well as by this installer.
    """

    remove: Callable[[str], str]
    noun: str
    block: str


_LIMIT_REMOVALS = {
    "codex-config": _LimitRemoval(
        without_codex_agent_limits, "Codex config", "managed agent limits block"
    ),
    "grok-config": _LimitRemoval(
        without_grok_subagent_limits, "Grok config", "managed subagent limits block"
    ),
}


def _limit_block_removal(path: Path, dry_run: bool, spec: _LimitRemoval) -> tuple[bool, str]:
    """Lift one host's managed limit block back out of its own config.

    The file is the user's and the markers are not a deed to what sits between
    them -- a host CLI appends its own tables in there. Only the keys the
    installer wrote come out, so the removal is the merge run backwards rather
    than a delete. A file left holding nothing but whitespace held nothing but
    those keys, so it goes. Returns whether the entry is settled, and its
    action.
    """

    if not path.is_file():
        return True, "already absent"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        return False, f"review {spec.noun}; could not read it: {error}; not changed"
    try:
        remainder = spec.remove(text)
    except ValueError as error:
        return False, f"review {spec.noun}; {error}; not changed"
    if remainder == text:
        return False, f"review {spec.noun}; the {spec.block} is not in it; not changed"
    empty = not remainder.strip()
    verb = "would remove" if dry_run else "removed"
    action = (
        f"{verb} {spec.noun} written by the installer"
        if empty
        else f"{verb} the {spec.block} from {spec.noun}"
    )
    if dry_run:
        return True, action
    try:
        if empty:
            path.unlink()
        else:
            path.write_text(remainder, encoding="utf-8")
    except OSError as error:
        return False, f"remove the {spec.block} manually; it failed here: {error}"
    return True, action


def _uninstall_boundary(path: Path, scope: str, project_root: Path | None) -> Path:
    """Codex prompts live under the user home even for project installs, and a
    ``CLAUDE_CONFIG_DIR`` / ``CODEX_HOME`` / ``GROK_HOME`` install lives
    outside it entirely."""

    roots = [_claude_user_home(), _codex_user_home(), _grok_user_home()]
    if scope == "project":
        roots.insert(0, _require_project_root(project_root))
    for root in roots:
        try:
            path.resolve().relative_to(root.resolve())
            return root
        except (OSError, ValueError):
            continue
    return Path.home()


def _auto_remove_path_is_safe(
    path: Path, kind: str, scope: str, project_root: Path | None
) -> bool:
    resolver = _AUTO_REMOVE_BOUNDARIES.get(kind)
    if resolver is None:
        return False
    boundary, scope_boundary = resolver(scope, project_root)
    try:
        boundary.resolve().relative_to(scope_boundary.resolve())
        path.resolve().relative_to(boundary.resolve())
    except (OSError, ValueError):
        return False
    return not path.is_symlink()


def run_uninstall(scope: str, project_root: Path | None, dry_run: bool) -> dict:
    scope_home = _uninstall_home(scope, project_root)
    receipt_path = scope_home / orchflows_home.RECEIPT_FILENAME
    receipt = _load_json(receipt_path)
    if receipt is None:
        return {
            "skill_actions": [],
            "manual_actions": [],
            "note": f"no valid receipt found at {receipt_path}",
        }

    skill_actions = []
    manual_actions = []
    planned_removals = set()
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
            if install_action == "kept":
                action = f"leave {kind} file as it is; the installer never wrote it{detail_suffix}"
            elif install_action == "created":
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

        noun, review_noun = _REMOVAL_NOUNS.get(kind, _DEFAULT_NOUNS)
        if not _auto_remove_path_is_safe(path, kind, scope, project_root):
            manual_actions.append(
                {
                    "path": str(path),
                    "action": f"review {review_noun}; path is outside its verified install boundary; not removed",
                }
            )
            continue

        # The entries whose removal is not a delete. They run ahead of the
        # hash gate below on purpose: what comes out is keyed on the lines the
        # installer wrote, so it stays exact however much of the file -- or of
        # the marked block itself -- has changed since the install wrote it.
        if kind in _LIMIT_REMOVALS:
            settled, action = _limit_block_removal(path, dry_run, _LIMIT_REMOVALS[kind])
            bucket = skill_actions if settled else manual_actions
            bucket.append({"path": str(path), "action": action})
            continue

        if not path.is_file():
            skill_actions.append({"path": str(path), "action": "already absent"})
            continue

        if install_action != "created":
            manual_actions.append(
                {
                    "path": str(path),
                    "action": (
                        f"review installer-replaced {review_noun}; no original backup was recorded; not removed"
                        if install_action == "replaced"
                        else f"review {review_noun}; install action is unknown; not removed"
                    ),
                }
            )
            continue

        installed_hash = entry.get("sha256")
        try:
            current_hash = _sha256_file(path)
        except OSError as error:
            manual_actions.append(
                {"path": str(path), "action": f"review {review_noun}; could not verify: {error}"}
            )
            continue

        if not installed_hash or current_hash != installed_hash:
            reason = "no install hash" if not installed_hash else "modified since install"
            manual_actions.append(
                {"path": str(path), "action": f"review {review_noun}; {reason}; not removed"}
            )
            continue

        if dry_run:
            skill_actions.append({"path": str(path), "action": f"would remove unchanged {noun}"})
            planned_removals.add(path.resolve())
            continue
        try:
            path.unlink()
        except OSError as error:
            manual_actions.append(
                {"path": str(path), "action": f"remove {review_noun} manually; automatic removal failed: {error}"}
            )
            continue
        prune_boundary = (
            _frontend_home()
            if kind == "frontend-asset"
            else _uninstall_boundary(path, scope, project_root)
        )
        _prune_empty_dirs(path.parent, prune_boundary)
        skill_actions.append({"path": str(path), "action": f"removed unchanged {noun}"})

    frontend = receipt.get("frontend")
    if isinstance(frontend, dict) and frontend.get("uninstall") == "receipt-guarded":
        frontend_home = Path(str(frontend.get("home", "")))
        expected_home = _frontend_home()
        try:
            safe_home = (
                not frontend_home.is_symlink()
                and frontend_home.resolve() == expected_home.resolve()
            )
        except OSError:
            safe_home = False
        remaining = ()
        if safe_home and frontend_home.is_dir():
            try:
                remaining = tuple(
                    path for path in frontend_home.rglob("*")
                    if path.is_file() and path.resolve() not in planned_removals
                )
            except OSError:
                remaining = (frontend_home,)
        if safe_home and frontend_home.is_dir() and not remaining:
            if dry_run:
                skill_actions.append(
                    {
                        "path": str(frontend_home),
                        "action": "would remove empty frontend distribution",
                    }
                )
            else:
                frontend_home.rmdir()
                skill_actions.append(
                    {
                        "path": str(frontend_home),
                        "action": "removed empty frontend distribution",
                    }
                )
        elif frontend_home.exists():
            manual_actions.append(
                {
                    "path": str(frontend_home),
                    "action": "review frontend distribution; modified or outside its verified boundary; not removed",
                }
            )

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

    runtime = receipt.get("runtime")
    if isinstance(runtime, dict) and runtime.get("home"):
        manual_actions.append(
            {
                "path": str(runtime["home"]),
                "action": (
                    "retained private runtime; remove manually after installed "
                    "orchflows commands no longer need it"
                ),
            }
        )

    manual_actions.append(
        {"path": str(receipt_path), "action": "delete receipt after completing manual cleanup"}
    )
    return {
        "skill_actions": skill_actions,
        "manual_actions": manual_actions,
        "receipt": str(receipt_path),
    }
