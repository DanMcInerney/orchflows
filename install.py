#!/usr/bin/env python3
"""Install orchflows for Claude Code, Codex and Grok Build from a git clone.

Cross-platform (Windows + POSIX), pathlib throughout, never symlinks. User
scope is primary and auto-detects its hosts: a host's half runs only when its
own CLI is on ``PATH``, and if none is found it warns and exits successfully
without writing anything. ``CLAUDE_CONFIG_DIR``, ``CODEX_HOME`` and
``GROK_HOME`` each replace their host's default home, matching that CLI.

- ``~/.orchflows/`` (private Python runtime, library, scripts, receipt, the
  rendered ``host-block.md``). The library also carries a flat, host-agnostic
  ``lib/by-name/<orch-name>/SKILL.md`` index: one deterministic path per
  canonical package (every skill tier plus packs), each a redirect pointer to
  its tiered source so a name resolves without guessing a sublayer. The
  pointer never copies the body, so it carries no relative links — an agent
  follows it to the tiered file, where every ``references/`` and ``../../../``
  link resolves from its authored location.
Host-specific destinations, frontmatter, launch fields, profiles, markers,
and capability establishment are rendered from ``hosts/*.json`` before the
plan is built.

- Claude Code — rendered skill and composition adapters, role agents,
  instructions, and concurrency settings.
- Codex — rendered prompts and one exact redirect skill per discovered
  canonical skill or composition, plus role agents, instructions, agent
  limits, and dangling-hook warnings.
- Grok Build — rendered skills, role agents, instructions, and subagent
  limits.

Installation has one scope: user. Legacy project receipts remain accepted by
``--project PATH --uninstall`` only, so older versions' installations can
still be cleaned up conservatively without recreating project artifacts.

The receipt records ``source_commit`` (the installed-from repo's git HEAD,
read from a clone or a worktree checkout); a rerun whose HEAD has moved prints
the drift, and a null commit says on stderr which read came up empty. A
receipt that will not read is refused, never overwritten as if absent.

``--dry-run`` builds and prints the exact same plan an install would apply,
including whether the private runtime would be created, reused or repaired,
without writing anything. ``--uninstall`` removes only what it generated
and finds unchanged: entrypoints and role agents on all three hosts, plus
the two managed TOML config blocks, lifted key by key rather than deleted.
It prints manual cleanup for every other path in the scope's
``receipt.json`` (gracefully, even for a receipt from an older, full
project install) and retains that receipt until cleanup is complete.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

MIN_PYTHON = (3, 9)
if sys.version_info < MIN_PYTHON:
    _running = ".".join(str(part) for part in sys.version_info[:3])
    raise SystemExit(
        f"error: orchflows needs Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or "
        f"newer, but {sys.executable} is {_running}. Point a newer "
        f"interpreter at this script, or run `uv run --no-project python "
        f"install.py`."
    )

SCRIPT_NAMES = (
    "browser_game_validate.py",
    "cutcheck.py",
    "doclint.py",
    "friction.py",
    "migrate_state.py",
    "packs.py",
    "search_plan.py",
    "state_root.py",
    "tickets.py",
    "trace.py",
    "ui.py",
    "workspace.py",
)
SCRIPT_SUPPORT_PREFIXES = (
    "tickets",
    "ui",
    "cutcheck",
    "packs",
    "search_plan",
    "trace",
    "workspace",
    "migrate_state",
)
_LOCAL_ROOT = Path(__file__).resolve().parent
if str(_LOCAL_ROOT) not in sys.path:
    sys.path.insert(0, str(_LOCAL_ROOT))
_loaded_installer = sys.modules.get("installer")
if _loaded_installer is not None:
    _loaded_path = Path(getattr(_loaded_installer, "__file__", "")).resolve()
    if _LOCAL_ROOT / "installer" not in (_loaded_path, *_loaded_path.parents):
        for _module_name in tuple(sys.modules):
            if _module_name == "installer" or _module_name.startswith("installer."):
                del sys.modules[_module_name]


def discover_script_names(scripts_dir: Path) -> tuple[str, ...]:
    """Return entrypoints plus flat helpers owned by compatibility facades."""

    entrypoints = set(SCRIPT_NAMES)
    support = sorted(
        path.name
        for path in scripts_dir.glob("*.py")
        if path.name not in entrypoints
        and any(path.stem.startswith(f"{prefix}_") for prefix in SCRIPT_SUPPORT_PREFIXES)
    )
    return SCRIPT_NAMES + tuple(support)


from installer import planning as _planning
from installer import presentation as _presentation
from installer import application as _application
from installer import runtime as _runtime
from installer.doctor import inspect_installation, run_quick
from installer.application import (
    _diverged_role_agents,
    _installed_file,
    _load_json,
    _prompt_keep_role_agents,
    _prune_empty_dirs,
    _remove_stale,
    _sha256_file,
    apply_plan as _apply_plan,
    print_summary,
)
from installer.foundation import (
    AUTO_REMOVE_KINDS,
    CANONICAL_DIRS,
    CLAUDE_ADAPTER_SETS,
    CLAUDE_CLI_CANDIDATES, CLAUDE_MAX_TOOL_USE_CONCURRENCY,
    CLAUDE_SETTINGS_SCHEMA,
    CODEX_CLI_CANDIDATES,
    CODEX_LIMITS_END, CODEX_LIMITS_START,
    CODEX_MAX_DEPTH,
    CODEX_MAX_THREADS,
    GROK_CLI_CANDIDATES, GROK_LIMITS_END, GROK_LIMITS_START,
    GROK_MAX_CONCURRENT, GROK_MAX_DEPTH,
    HOST_BLOCK_TEMPLATE,
    MIN_PYTHON,
    PROFILES_MD,
    PROFILE_ROLES,
    REPO_ROOT,
    SHARED_ADAPTER_NAMES,
    STATE_HOME_ENV_VAR,
    STATE_SINK_SUBPATH,
    _bin_dir,
    _claude_agents_dir,
    _claude_md_path,
    _claude_scope_home,
    _claude_settings_path,
    _claude_user_home,
    _codex_agents_dir, _codex_agents_path,
    _codex_config_path,
    _codex_hooks_warnings,
    _codex_scope_home, _codex_user_home,
    _frontend_home,
    _grok_agents_dir, _grok_config_path, _grok_rules_path,
    _grok_skills_dir, _grok_user_home,
    _iter_json_strings,
    _lib_home,
    _require_project_root,
    _runtime_dirs,
    _scope_home,
    _state_sink,
    tomllib,
)
from installer.managed_text import (
    grok_skill_text, render_grok_agent, render_claude_settings,
    render_codex_agent_limits as _render_codex_agent_limits,
    render_grok_subagent_limits as _render_grok_subagent_limits,
    render_host_block,
    upsert_import_line,
    upsert_marked_block,
    without_marked_block,
)
from installer.models import (
    BlockPlan,
    ConfigPlan,
    ImportPlan,
    Plan,
    _host_block_content,
    _frontend_manifest,
    _frontend_manifest_identity,
    _is_build_artifact,
)
from installer.packages import (
    accepted_source_commit,
    FORK_ARRIVAL_CLAUSE,
    ROLE_INSTRUCTIONS,
    TEMPLATE_MANIFEST,
    _git_dirs,
    _role_description,
    by_name_pointer_text,
    claude_role_adapter_text,
    discover_packages,
    discover_templates,
    frontmatter_field,
    host_legal_frontmatter,
    load_role_profiles,
    render_claude_agent,
    render_codex_agent,
    resolve_source_commit,
    resolved_python_interpreter,
    source_commit_drift_message,
    source_commit_warning,
    split_frontmatter,
    template_adapter_body,
    template_markers,
)
from installer.hosts import HOSTS_DIR, HOST_ADAPTERS_DIR, load_host_adapters
from installer.planning import _mints_claude_adapter, detect_hosts, plan_entry_count
from installer.uninstall import (
    _auto_remove_path_is_safe,
    _uninstall_boundary,
    run_uninstall,
)
from installer import foundation as _foundation
from installer import managed_text as _managed_text
from installer import models as _models
from installer import packages as _packages

_discover_packages_impl = discover_packages
_detect_hosts_impl = detect_hosts

RUNTIME_METADATA_FILENAME = _runtime.RUNTIME_METADATA_FILENAME
RUNTIME_REQUIREMENTS = _runtime.RUNTIME_REQUIREMENTS
_dependency_environment = _runtime._dependency_environment
_read_runtime_metadata = _runtime._read_runtime_metadata
_runtime_metadata = _runtime._runtime_metadata
_runtime_requirement_lines = _runtime._runtime_requirement_lines
private_runtime_action = _runtime.private_runtime_action
private_runtime_home = _runtime.private_runtime_home
private_runtime_is_healthy = _runtime.private_runtime_is_healthy
private_runtime_is_owned = _runtime.private_runtime_is_owned
private_runtime_python = _runtime.private_runtime_python
venv = _runtime.venv

_build_private_runtime_impl = _runtime._build_private_runtime
_create_private_runtime_impl = _runtime._create_private_runtime


def _build_private_runtime(runtime_home: Path) -> Path:
    return _build_private_runtime_impl(runtime_home)


def _create_private_runtime() -> Path:
    _runtime._build_private_runtime = _build_private_runtime
    return _create_private_runtime_impl()


def _sync_installer_seams() -> None:
    for module in (_foundation, _models, _packages, _planning):
        if hasattr(module, "REPO_ROOT"):
            module.REPO_ROOT = REPO_ROOT
    _managed_text.CODEX_MAX_THREADS = CODEX_MAX_THREADS
    _planning.detect_hosts = detect_hosts
    _planning.private_runtime_action = private_runtime_action
    _planning.private_runtime_is_healthy = private_runtime_is_healthy
    _models.private_runtime_python = private_runtime_python
    _runtime.RUNTIME_REQUIREMENTS = RUNTIME_REQUIREMENTS
    _runtime._build_private_runtime = _build_private_runtime
    _application._create_private_runtime = _create_private_runtime
    _application.private_runtime_is_healthy = private_runtime_is_healthy


def discover_packages():
    _sync_installer_seams()
    return _discover_packages_impl()


def detect_hosts(home: Path | None = None) -> tuple[bool, bool, bool]:
    return _detect_hosts_impl(home)


def render_codex_agent_limits(text: str) -> tuple[str, dict]:
    _sync_installer_seams()
    return _render_codex_agent_limits(text, tomllib)


def render_grok_subagent_limits(text: str) -> tuple[str, dict]:
    _sync_installer_seams()
    return _render_grok_subagent_limits(text, tomllib)


def _build_user_plan(claude_adapter_set: str = "all") -> Plan:
    _sync_installer_seams()
    return _planning._build_user_plan(
        claude_adapter_set, render_codex_agent_limits, discover_script_names,
        render_grok_subagent_limits,
    )


def build_plan(
    scope: str, project_root: Path | None, claude_adapter_set: str = "all"
) -> Plan:
    if scope != "user":
        raise ValueError("installation supports user scope only")
    _sync_installer_seams()
    return _planning.build_plan(
        scope,
        project_root,
        claude_adapter_set,
        render_codex_agent_limits,
        discover_script_names,
        render_grok_subagent_limits,
    )


def print_plan(plan: Plan) -> None:
    if plan.scope != "user":
        raise ValueError("installation supports user scope only")
    _presentation.print_plan(plan, resolve_source_commit())


def apply_plan(plan: Plan, keep_role_agents: bool | None = None, *, accepted_source: str | None = None, source_commit: str | None = None) -> dict:
    if plan.scope != "user":
        raise ValueError("installation supports user scope only")
    _sync_installer_seams()
    observed = resolve_source_commit() if source_commit is None else source_commit
    accepted_source_commit(observed, accepted_source, mutating=True)
    return _apply_plan(plan, observed, keep_role_agents)


# --- CLI -----------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    hosts = (__doc__ or "").splitlines()[0].partition("orchflows for ")[2].partition(" from ")[0]
    parser = argparse.ArgumentParser(description=f"Install or remove orchflows for {hosts}.")
    parser.add_argument(
        "command",
        nargs="?",
        choices=("doctor",),
        help="Inspect the user installation for bootstrap drift; write nothing.",
    )
    parser.add_argument("--user", action="store_true", help="Install scope: user (all sessions).")
    parser.add_argument(
        "--project",
        nargs="?",
        const=".",
        default=None,
        metavar="PATH",
        help="Legacy cleanup scope, optionally at PATH; requires --uninstall.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the prompts: user scope, and keep any role agent this machine has changed.",
    )
    parser.add_argument("--accepted-source", metavar="COMMIT", help="Require this exact composite-gate source commit.")
    parser.add_argument("--dry-run", action="store_true", help="Print the full plan; write nothing.")
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Inspect the user installation for bootstrap drift; write nothing.",
    )
    parser.add_argument("--quick", action="store_true", help="Doctor: compare only the receipt's source commit and host block, then exit; write nothing.")
    parser.add_argument(
        "--claude-adapters",
        choices=CLAUDE_ADAPTER_SETS,
        default="all",
        help=(
            "Claude skill adapters to mint: all canonical names (default), or the "
            f"bounded compatibility set ({', '.join(SHARED_ADAPTER_NAMES)}). "
            "Every other name still resolves at the flat by-name index."
        ),
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove unchanged generated skills and print receipt-based manual cleanup.",
    )
    return parser


def _resolve_scope(args) -> tuple[str, Path | None]:
    if args.user and args.project is not None:
        raise SystemExit("error: --user and --project are mutually exclusive")
    if args.project is not None and not args.uninstall:
        raise SystemExit("error: --project is only available with --uninstall for legacy cleanup")
    if args.uninstall and not args.user and args.project is None:
        raise SystemExit("error: --uninstall requires --user or --project [PATH]")
    if args.user:
        return "user", None
    if args.project is not None:
        return "project", Path(args.project).resolve()
    return "user", None


def main(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    doctor_requested = args.command == "doctor" or args.doctor or args.quick

    if doctor_requested and args.uninstall:
        print("error: doctor and --uninstall are mutually exclusive", file=sys.stderr)
        return 2

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

    source_commit = resolve_source_commit()
    # Uninstall has already returned above; what remains that is not a dry
    # run or a doctor probe consumes the checkout and must name the identity
    # its gate accepted.  A read-only path grades one only if given one.
    try:
        accepted_source_commit(
            source_commit, args.accepted_source,
            mutating=not (args.dry_run or doctor_requested),
        )
    except ValueError as error:
        print(f"error: refusing source identity: {error}", file=sys.stderr)
        return 1

    if args.quick:
        return run_quick(source_commit)

    try:
        plan = build_plan(scope, project_root, args.claude_adapters)
    except Exception as error:
        print(f"error: could not build install plan: {error}", file=sys.stderr)
        return 1

    if doctor_requested:
        report = inspect_installation(plan, current_source_commit=source_commit)
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
        return 0 if report["status"] == "coherent" else 1

    for warning in plan.warnings:
        print(warning)

    # Before the no-host exit, so a dry run always prints the plan it built
    # and its entry count. Returning 0 without printing anything read exactly
    # like a run that had planned the whole install.
    if args.dry_run:
        print_plan(plan)
        unresolved = source_commit_warning(source_commit)
        if unresolved:
            print(unresolved, file=sys.stderr)
        if plan.runtime_action == "refuse":
            print(
                f"error: refusing install because {private_runtime_home()} is "
                "not a healthy installer-owned runtime",
                file=sys.stderr,
            )
            return 1
        enabled = plan.claude_enabled or plan.codex_enabled or plan.grok_enabled
        if enabled and plan_entry_count(plan) == 0:
            print(
                "error: a host is enabled but the plan is empty; nothing would be installed",
                file=sys.stderr,
            )
            return 1
        return 0

    if scope == "user" and not (plan.claude_enabled or plan.codex_enabled or plan.grok_enabled):
        return 0

    try:
        old_receipt = _load_json(plan.receipt_path)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    try:
        receipt = apply_plan(plan, keep_role_agents=True if args.yes else None,
                             accepted_source=args.accepted_source, source_commit=source_commit)
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
