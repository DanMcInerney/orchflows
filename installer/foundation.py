"""Installer constants and scope-derived paths."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

# The floor this installer is written to and CI proves. Enforced here
# because install.py is the only file a user runs directly -- the shell
# wrappers just resolve an interpreter and hand it this script. Kept at 3.9
# deliberately: install.sh falls through to `python3`, which on a stock
# macOS is 3.9, and nothing in the tree needs newer syntax.
MIN_PYTHON = (3, 9)
if sys.version_info < MIN_PYTHON:
    _running = ".".join(str(part) for part in sys.version_info[:3])
    raise SystemExit(
        f"error: orchflows needs Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or "
        f"newer, but {sys.executable} is {_running}. Point a newer "
        f"interpreter at this script, or run `uv run --no-project python "
        f"install.py`."
    )

try:
    import tomllib
except ModuleNotFoundError:  # tomllib is 3.11+; MIN_PYTHON is lower.
    tomllib = None

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_DIRS = (
    "contracts",
    "rules",
    "docs",
    "skills",
    "packs",
    "compositions",
    "templates",
)
CLAUDE_CLI_CANDIDATES = ("claude", "claude.exe", "claude.cmd")
CODEX_CLI_CANDIDATES = ("codex", "codex.exe", "codex.cmd")
PROFILES_MD = REPO_ROOT / "skills" / "engines" / "orch-frontier" / "references" / "profiles.md"
HOST_BLOCK_TEMPLATE = REPO_ROOT / "templates" / "host-block.md"
CODEX_LIMITS_START = "# BEGIN ORCHFLOWS AGENT LIMITS"
CODEX_LIMITS_END = "# END ORCHFLOWS AGENT LIMITS"
PROFILE_ROLES = ("planner", "worker")
# The four names both hosts expose as first-class adapters; every other
# name resolves at ``by-name/``. The routed composition ``fix`` replaced the
# demoted ``orch-fix`` skill.
SHARED_ADAPTER_NAMES = ("orch-spec", "orch-frontier", "fix", "orch-build")
# The Codex redirect set is that same set, under its older name.
CODEX_SKILL_REDIRECT_NAMES = SHARED_ADAPTER_NAMES
CLAUDE_ADAPTER_SETS = ("all", "four")
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


# ``scripts/state_root.py`` owns this pair. The installer cannot import it: it
# runs before any script is installed. Stated once here, and linked rather than
# restated in prose.
STATE_HOME_ENV_VAR = "ORCHFLOWS_STATE_HOME"
STATE_SINK_SUBPATH = (".orchflows", "state")


def _state_sink() -> Path:
    """The one user-scope sink an install of either scope seeds.

    The override is honoured for two reasons, not one: a user who redirects
    the sink gets the root they actually read seeded, and the test suite's own
    redirect keeps an installer test that forgets to fake ``Path.home`` off the
    real sink. A resolver the installer ignored would sit outside that guard.
    """

    override = os.environ.get(STATE_HOME_ENV_VAR, "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home().joinpath(*STATE_SINK_SUBPATH)


def _runtime_dirs(scope: str, project_root: Path | None) -> list[Path]:
    """The directories an install seeds — the same four in either scope.

    Durable state is user-scope: one sink, reached from any repository, so a
    project install seeds nothing project-local. ``bin/`` is not state and is
    absent here; the script-copy step creates it where ``_bin_dir`` puts it.
    """

    if scope != "user":
        _require_project_root(project_root)
    sink = _state_sink()
    return [
        sink / "tickets",
        sink / "runs",
        sink / "friction",
        sink / "improvement" / "proposals",
    ]


def _claude_user_home() -> Path:
    """Claude Code's user config directory. ``CLAUDE_CONFIG_DIR`` overrides the
    ``~/.claude`` default, and the CLI reads only that env var — a relocated
    config directory has no project-local equivalent, so project scope is
    unaffected."""

    override = os.environ.get("CLAUDE_CONFIG_DIR", "").strip()
    return Path(override).expanduser() if override else Path.home() / ".claude"


def _claude_scope_home(scope: str, project_root: Path | None) -> Path:
    if scope == "user":
        return _claude_user_home()
    return _require_project_root(project_root) / ".claude"


def _claude_md_path(scope: str, project_root: Path | None) -> Path:
    if scope == "user":
        return _claude_user_home() / "CLAUDE.md"
    return _require_project_root(project_root) / "CLAUDE.md"


def _claude_settings_path(scope: str, project_root: Path | None) -> Path:
    return _claude_scope_home(scope, project_root) / "settings.json"


def _claude_agents_dir(scope: str, project_root: Path | None) -> Path:
    return _claude_scope_home(scope, project_root) / "agents"


def _codex_user_home() -> Path:
    # Codex prompts have no project-local equivalent. Native role agents and
    # config use ``_codex_scope_home`` and therefore follow the selected scope.
    # ``CODEX_HOME`` overrides the ``~/.codex`` default, as the Codex CLI reads it.
    override = os.environ.get("CODEX_HOME", "").strip()
    return Path(override).expanduser() if override else Path.home() / ".codex"


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
        return _codex_user_home() / "AGENTS.md"
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
    except (OSError, json.JSONDecodeError) as error:
        # Not [] -- that is this preflight's word for "no dangling paths".
        return [f"warning: {hooks_path} could not be read ({error}); its orchflows paths were not checked"]
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


