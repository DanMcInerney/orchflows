"""Conservative receipt-driven uninstall planning and application."""

from __future__ import annotations

import json
from pathlib import Path

from .application import _load_json, _prune_empty_dirs, _sha256_file
from .foundation import (
    AUTO_REMOVE_KINDS,
    GROK_AUTO_REMOVE_KINDS,
    GROK_LIMITS_END,
    GROK_LIMITS_START,
    _claude_scope_home,
    _claude_user_home,
    _codex_user_home,
    _frontend_home,
    _grok_agents_dir,
    _grok_rules_path,
    _grok_skills_dir,
    _grok_user_home,
    _require_project_root,
    _scope_home,
)
from .managed_text import without_marked_block

# --- uninstall ---------------------------------------------------------

# Each Grok kind's own directory, tightest first: a receipt entry may only
# remove a file from the place the installer put that kind. ``grok-config``
# is the file directly at the home, so the home is its boundary.
_GROK_BOUNDARIES = {
    "grok-skill": _grok_skills_dir,
    "grok-agent": _grok_agents_dir,
    "grok-rules": lambda: _grok_rules_path().parent,
    "grok-config": _grok_user_home,
}

# What the report calls the thing it removed, and what a review line calls
# the same thing. Defaulting to the skill wording keeps every Claude and
# Codex line exactly as it was.
_DEFAULT_NOUNS = ("skill", "skill file")
_REMOVAL_NOUNS = {
    "frontend-asset": ("frontend asset", "frontend asset"),
    "grok-skill": ("Grok skill", "Grok skill file"),
    "grok-agent": ("Grok role agent", "Grok role agent file"),
    "grok-rules": ("Grok instruction file", "Grok instruction file"),
    "grok-config": ("Grok config", "Grok config"),
}


def _grok_config_removal(path: Path, dry_run: bool) -> tuple[bool, str]:
    """Lift the managed ``[subagents]`` block back out of the Grok config.

    The file is the user's; only the marked block inside it is the
    installer's, so the removal here is the merge run backwards rather than a
    delete. A file left holding nothing but whitespace held nothing but that
    block, so it goes. Returns whether the entry is settled, and its action.
    """

    if not path.is_file():
        return True, "already absent"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        return False, f"review Grok config; could not read it: {error}; not changed"
    try:
        remainder = without_marked_block(text, GROK_LIMITS_START, GROK_LIMITS_END)
    except ValueError as error:
        return False, f"review Grok config; {error}; not changed"
    if remainder == text:
        return False, "review Grok config; the managed subagent limits block is not in it; not changed"
    empty = not remainder.strip()
    verb = "would remove" if dry_run else "removed"
    action = (
        f"{verb} Grok config written by the installer"
        if empty
        else f"{verb} the managed subagent limits block from Grok config"
    )
    if dry_run:
        return True, action
    try:
        if empty:
            path.unlink()
        else:
            path.write_text(remainder, encoding="utf-8")
    except OSError as error:
        return False, f"remove the managed subagent limits block manually; it failed here: {error}"
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
    if kind == "frontend-asset":
        boundary = _frontend_home()
    elif kind == "adapter":
        boundary = _claude_scope_home(scope, project_root) / "skills"
    elif kind == "codex-skill":
        boundary = _codex_user_home() / "skills"
    elif kind in GROK_AUTO_REMOVE_KINDS:
        boundary = _GROK_BOUNDARIES[kind]()
    else:
        boundary = _codex_user_home() / "prompts"
    if kind == "frontend-asset":
        scope_boundary = _frontend_home().parent
    elif kind == "adapter":
        scope_boundary = (
            _require_project_root(project_root) if scope == "project" else _claude_user_home()
        )
    elif kind in GROK_AUTO_REMOVE_KINDS:
        scope_boundary = _grok_user_home()
    else:
        scope_boundary = _codex_user_home()
    try:
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

        # The one entry whose removal is not a delete. It runs ahead of the
        # hash gate below on purpose: the block is found by its own markers,
        # so lifting it out stays exact however much of the file around it
        # the user has changed since the install wrote it.
        if kind == "grok-config":
            settled, action = _grok_config_removal(path, dry_run)
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
