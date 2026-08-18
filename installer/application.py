"""Receipt-backed installation application."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .foundation import (
    _claude_agents_dir,
    _claude_md_path,
    _claude_scope_home,
    _claude_settings_path,
    _codex_agents_dir,
    _codex_agents_path,
    _codex_config_path,
    _codex_user_home,
)
from .managed_text import upsert_import_line, upsert_marked_block
from .models import Plan

# --- apply -----------------------------------------------------------------


def _load_json(path: Path):
    """``None`` only when there is no file. A file that will not read or will
    not parse raises: read as ``None`` it would pass for a first install, and
    the receipt it could not read is the only record of what to remove and
    what this installer wrote."""

    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{path} is unreadable ({error}); move it aside and rerun") from error


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


def _diverged_role_agents(plan: Plan, old_receipt: dict | None) -> list:
    """Role agents on disk whose content is not what this install would write.

    Returned rather than raised: the ordinary reason is a machine
    deliberately running different bindings, and the caller asks before
    replacing one. A path that is not a regular file still raises, since
    writing through it would clobber something this installer never made.
    """

    old_entries = {
        (entry.get("path"), entry.get("kind")): entry
        for entry in (old_receipt or {}).get("files", [])
    }
    unwritable, diverged = [], []
    for kind, files in (
        ("claude-agent", plan.claude_agents),
        ("codex-agent", plan.codex_agents),
    ):
        for path, desired in files:
            if not path.exists() and not path.is_symlink():
                continue
            if not path.is_file() or path.is_symlink():
                unwritable.append(f"{path} (not a regular file)")
                continue
            if path.read_text(encoding="utf-8") == desired:
                continue
            old_entry = old_entries.get((str(path), kind))
            recorded_hash = old_entry.get("sha256") if old_entry else None
            if not recorded_hash:
                diverged.append((path, kind, "not written by this installer"))
            elif _sha256_file(path) != recorded_hash:
                diverged.append((path, kind, "edited since the last install"))

    if unwritable:
        raise FileExistsError(
            "refusing to write role profile(s) that are not regular files:\n  "
            + "\n  ".join(unwritable)
            + "\nMove or remove them, then reinstall."
        )
    return diverged


def _prompt_keep_role_agents(diverged: list) -> bool:
    print("These orchflows role agents differ from the shipped bindings:")
    for path, _kind, reason in diverged:
        print(f"  {path} ({reason})")
    print("Keep them? [Y] keep this machine's  [n] overwrite with the defaults")
    try:
        choice = input("> ").strip().lower()
    except EOFError:
        # Non-interactive: keep, because reverting a deliberate binding
        # unasked is the one outcome nobody can undo from the receipt.
        choice = ""
    return choice != "n"


def apply_plan(
    plan: Plan, source_commit: str | None, keep_role_agents: bool | None = None
) -> dict:
    old_receipt = _load_json(plan.receipt_path)
    diverged = _diverged_role_agents(plan, old_receipt)
    # A kept agent stays in the plan so ``_remove_stale`` still counts it as
    # wanted; only its write is skipped. Dropping it from the plan would
    # delete the very file the answer asked to keep. It is left out of the
    # receipt too, so the next install asks again rather than silently
    # reverting a binding whose hash it had adopted as its own.
    kept_role_agents = set()
    if diverged:
        keep = _prompt_keep_role_agents(diverged) if keep_role_agents is None else keep_role_agents
        if keep:
            kept_role_agents = {(str(path), kind) for path, kind, _ in diverged}
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
                if (str(dest), kind) in kept_role_agents:
                    print(f"keeping this machine's {dest}")
                    continue
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

    # Day-zero documents. Day zero happens once: a document the project
    # already holds is left byte-identical and only recorded, because the
    # installer owns the skeleton, never the project's own thinking.
    for document in plan.day_zero:
        existed = document.dest.is_file()
        if not existed:
            document.dest.parent.mkdir(parents=True, exist_ok=True)
            document.dest.write_text(document.content, encoding="utf-8")
        # "created" once this installer has ever written the document — on
        # this run, or on an earlier one whose receipt says so — and "kept"
        # only while it never has. Uninstall reads this to know which is
        # which, so a kept document the project later removed and this run
        # rewrote turns "created" rather than inheriting "kept".
        old_entry = old_entries.get((str(document.dest), document.kind), {})
        action = "created" if not existed else (old_entry.get("install_action") or "kept")
        written_files.append(_installed_file(document.dest, document.kind, action))

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
        "source_commit": source_commit,
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
        print(f"  detected Claude Code CLI: {'yes' if plan.claude_enabled else 'no'}")
        print(f"  detected Codex CLI: {'yes' if plan.codex_enabled else 'no'}")
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
