"""Stage the executable payload and retain a recoverable old installation.

The installation lock precedes all run locks. Issuance and dispatch take the
same lock, so the nonterminal-reference census remains valid until receipt
publication. Until per-reference resolution is available, any nonterminal
ticket conservatively protects every existing lib/bin byte, including bytes
that were removed from the source checkout. Receipt identity alone is not a
payload change.
"""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from scripts import orchflows_node, state_root
from scripts.tickets_format import TERMINAL_STATES, VALID_STATUSES, _parse_frontmatter
from .models import _frontend_manifest_identity


def _state(plan):
    if plan.scope_home.resolve() == state_root.orchflows_home().resolve():
        return state_root.state_root()
    return plan.scope_home / "state"


def _active(plan, previously_installed):
    root = _state(plan) / "tickets"
    if not root.exists() and not previously_installed:
        return []
    try:
        if not root.is_dir() or root.is_symlink():
            raise OSError("ticket census directory is missing or not a regular directory")
        active = []
        for run in root.iterdir():
            if not run.is_dir() or run.is_symlink():
                raise OSError(f"unexpected ticket census entry: {run}")
            for path in run.iterdir():
                if path.suffix != ".md":
                    continue
                if not path.is_file() or path.is_symlink():
                    raise OSError(f"unreadable ticket reference: {path}")
                data = _parse_frontmatter(path.read_text(encoding="utf-8"))
                if data.get("id") != path.stem or data.get("run") != run.name:
                    raise ValueError(f"ticket identity does not match its installed location: {path}")
                status = data.get("status")
                if status not in VALID_STATUSES:
                    raise ValueError(f"unknown ticket status at {path}: {status!r}")
                if status not in TERMINAL_STATES:
                    active.append(str(path))
        return active
    except (OSError, ValueError, TypeError) as error:
        raise RuntimeError(f"active-reference census unavailable at {root}: {error}; "
                           "restore readable installed ticket state before retrying installation") from error


def _files(root):
    if not root.exists():
        return {}
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError(f"installation payload is not a regular directory: {root}")
    result = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise RuntimeError(f"installation payload contains a symlink: {path}")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in (".pyc", ".pyo"):
            result[path.relative_to(root)] = _digest(path)
    return result


def _digest(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stage(plan, root):
    payloads = []
    for name, live, copies in (("lib", plan.lib_home, plan.lib_copies),
                               ("bin", plan.bin_dir, plan.scripts if plan.manage_host_surfaces else [])):
        if not copies:
            continue
        stage = root / name
        stage.mkdir()
        for source, destination in copies:
            relative = destination.relative_to(live)
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            if _digest(target) != _digest(source):
                raise RuntimeError(f"staged copy differs: {source}")
        if name == "lib":
            for destination, content in plan.by_name:
                target = stage / destination.relative_to(live)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            # Only the manifest's own declared tooling is prepared, never
            # arbitrary nested package manifests discovered in dependencies.
            declarations = [path.parent for path in stage.rglob("package.json")
                            if "node_modules" not in path.parts
                            and (path.parent / "SKILL.md").is_file()]
            for package in declarations:
                result = orchflows_node.ensure("workflow", package.name, package)
                if result["action"] == "skipped":
                    raise RuntimeError(f"staged dependency preparation refused: {result['detail']}")
                stamp_path = orchflows_node.modules_dir(package) / orchflows_node.STAMP_NAME
                stamp = json.loads(stamp_path.read_text(encoding="utf-8"))
                stamp["lockfile"] = str(live / Path(stamp["lockfile"]).relative_to(stage))
                stamp_path.write_text(json.dumps(stamp, sort_keys=True) + "\n", encoding="utf-8")
        for path in stage.rglob("*.py"):
            if "node_modules" not in path.parts:
                ast.parse(path.read_bytes(), filename=str(path))
        payloads.append((live, stage))
    if plan.frontend_action is not None:
        if plan.frontend_action == "refuse":
            raise RuntimeError(f"install requires healthy frontend assets at {plan.frontend_home}")
        if plan.frontend_action == "reuse":
            if _frontend_manifest_identity(plan.frontend_home) != plan.frontend_manifest_sha256:
                raise RuntimeError(f"frontend assets changed after planning: {plan.frontend_home}")
        else:
            stage = root / "ui"
            stage.mkdir()
            for source, destination in plan.frontend_assets:
                target = stage / destination.relative_to(plan.frontend_home)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            if _frontend_manifest_identity(stage) != plan.frontend_manifest_sha256:
                raise RuntimeError("staged frontend assets do not match the planned manifest")
            payloads.append((plan.frontend_home, stage))
    return payloads


def _surface_paths(plan, old):
    paths = {plan.receipt_path}
    for field in ("claude_adapters", "codex_prompts", "codex_skills", "claude_agents",
                  "codex_agents", "grok_skills", "grok_agents"):
        paths.update(path for path, _ in getattr(plan, field))
    paths.update(entry.dest for entry in (*plan.configs, *plan.blocks))
    paths.update(entry.dest for entry in (plan.host_block, plan.grok_rules, plan.claude_import)
                 if entry is not None)
    for entry in (old or {}).get("files", []):
        if entry.get("kind") not in ("lib", "script", "by-name", "frontend-asset"):
            paths.add(Path(entry["path"]))
    if plan.home_ring:
        paths.update(plan.home_ring / name for name in (".gitignore", "lib.version"))
    return paths


@contextmanager
def publication(plan, old):
    """Yield staged live payloads; on failure restore or name intact backups."""

    plan.scope_home.mkdir(parents=True, exist_ok=True)
    pending = list(plan.scope_home.glob(".install-transaction-*/recovery.json"))
    if pending:
        raise RuntimeError(f"unfinished installation recovery at {pending[0]}; restore its recorded backups before retrying")
    root = Path(tempfile.mkdtemp(prefix=".install-transaction-", dir=plan.scope_home))
    moves, surfaces = [], {}
    recover = False
    try:
        payloads = _stage(plan, root)
        active = _active(plan, bool(old) or plan.lib_home.exists() or plan.bin_dir.exists())
        changes = []
        for live, stage in payloads:
            before, after = _files(live), _files(stage)
            changes.extend(str(live / relative) for relative in before.keys() | after.keys()
                           if before.get(relative) != after.get(relative))
        if active:
            if changes:
                raise RuntimeError("installation would change bytes protected by active references: "
                                   + ", ".join(active) + "; first changed path: " + changes[0]
                                   + "; finish or retire owning assignments, then retry")
            # No directory rename gap for readers of unchanged active bytes.
            payloads = []
        if changes and (plan.bin_dir / "tickets.py").is_file():
            required = ("tickets_install_guard.py", "tickets_issue.py", "tickets_attempts.py",
                        "tickets_dispatch_facade.py", "tickets_mint.py", "tickets_frame.py")
            coordinated = all((plan.bin_dir / name).is_file() and "installation_lock" in
                              (plan.bin_dir / name).read_text(encoding="utf-8") for name in required)
            if not coordinated:
                raise RuntimeError("installed writers do not coordinate with installation; old bytes retained. "
                                   "Use the offline migration in installer/README.md: finish all active work, "
                                   "stop old clients and disable launches, park the old bin intact, then rerun. "
                                   "A new lock alone cannot exclude old writers.")
        for index, path in enumerate(sorted(_surface_paths(plan, old))):
            if path.is_symlink() or (path.exists() and not path.is_file()):
                raise RuntimeError(f"installation surface is not a regular file: {path}")
            backup = root / "surfaces" / str(index)
            if path.exists():
                backup.parent.mkdir(exist_ok=True)
                shutil.copy2(path, backup)
                surfaces[path] = backup
            else:
                surfaces[path] = None
        journal = {"payloads": [{"live": str(live), "backup": str(root / (stage.name + "-old"))}
                                for live, stage in payloads],
                   "surfaces": {str(path): str(backup) if backup else None for path, backup in surfaces.items()}}
        (root / "recovery.json").write_text(json.dumps(journal, indent=2), encoding="utf-8")
        for live, stage in payloads:
            backup = root / (stage.name + "-old")
            existed = live.exists()
            if existed:
                live.replace(backup)
            moves.append((live, backup if existed else None))
            stage.replace(live)
        yield
        (_state(plan) / "tickets").mkdir(parents=True, exist_ok=True)
    except BaseException as error:
        failures = []
        for path, backup in surfaces.items():
            try:
                if backup:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup, path)
                elif path.exists():
                    if path == plan.receipt_path and not old and plan.runtime_action is not None:
                        # A first runtime build is retained by policy. Keep its
                        # intent receipt so uninstall can discover that owner.
                        value = json.loads(path.read_text(encoding="utf-8"))
                        if value.get("install_in_progress"):
                            continue
                    path.unlink()
            except OSError as failure:
                failures.append(str(failure))
        for live, backup in reversed(moves):
            try:
                if live.exists():
                    shutil.rmtree(live)
                if backup:
                    backup.replace(live)
            except OSError as failure:
                failures.append(str(failure))
        if failures:
            recover = True
            raise RuntimeError(f"installation interrupted: {error}; intact backups and recovery map retained at "
                               f"{root}; rollback errors: {failures}") from error
        raise
    finally:
        if not recover:
            shutil.rmtree(root)
