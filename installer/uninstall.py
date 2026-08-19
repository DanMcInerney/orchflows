"""Conservative receipt-driven uninstall planning and application."""

from __future__ import annotations

import json
from pathlib import Path

from .application import _load_json, _prune_empty_dirs, _sha256_file
from .foundation import (
    AUTO_REMOVE_KINDS,
    _claude_scope_home,
    _claude_user_home,
    _codex_user_home,
    _require_project_root,
    _scope_home,
)

# --- uninstall ---------------------------------------------------------


def _uninstall_boundary(path: Path, scope: str, project_root: Path | None) -> Path:
    """Codex prompts live under the user home even for project installs, and a
    ``CLAUDE_CONFIG_DIR`` / ``CODEX_HOME`` install lives outside it entirely."""

    roots = [_claude_user_home(), _codex_user_home()]
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
    if kind == "adapter":
        boundary = _claude_scope_home(scope, project_root) / "skills"
    elif kind == "codex-skill":
        boundary = _codex_user_home() / "skills"
    else:
        boundary = _codex_user_home() / "prompts"
    if kind == "adapter":
        scope_boundary = (
            _require_project_root(project_root) if scope == "project" else _claude_user_home()
        )
    else:
        scope_boundary = _codex_user_home()
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
