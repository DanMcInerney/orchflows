"""Installer constants and scope-derived paths."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

from scripts import _bootstrap, state_root

from .hosts import (
    HOST_ADAPTERS_DIR,
    HOSTS_DIR,
    PROFILE_ROLES,
    host_item_path,
    load_host_adapters,
    marker,
)

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

# install.py, the sole entry point, has already put the repository root
# on sys.path before importing this module, so the fact is read from the
# leaf rather than re-walked here.
REPO_ROOT = _bootstrap.ROOT
READER_ROOT = REPO_ROOT / "reader"
_HOST_ADAPTERS = load_host_adapters()
CANONICAL_DIRS = (
    "contracts",
    "rules",
    "docs",
    "skills",
    "packs",
    "example-workflows",
    "templates",
    "hosts",
)
CLAUDE_CLI_CANDIDATES = tuple(_HOST_ADAPTERS["claude"]["cli_candidates"])
CODEX_CLI_CANDIDATES = tuple(_HOST_ADAPTERS["codex"]["cli_candidates"])
GROK_CLI_CANDIDATES = tuple(_HOST_ADAPTERS["grok"]["cli_candidates"])
PROFILES_MD = REPO_ROOT / "hosts" / "profiles.md"
HOST_BLOCK_TEMPLATE = REPO_ROOT / "templates" / "host-block.md"
CODEX_LIMITS_START = marker("codex", "agent_limits", _HOST_ADAPTERS)["start"]
CODEX_LIMITS_END = marker("codex", "agent_limits", _HOST_ADAPTERS)["end"]
GROK_LIMITS_START = marker("grok", "subagent_limits", _HOST_ADAPTERS)["start"]
GROK_LIMITS_END = marker("grok", "subagent_limits", _HOST_ADAPTERS)["end"]
# The routed names exposed by Claude's bounded adapter-set benchmark. Named
# skills outside this set remain explicit by-name invocations.
SHARED_ADAPTER_NAMES = ("orch-do", "orch-judge")
CLAUDE_ADAPTER_SETS = ("all", "four")
# Every Grok surface the installer writes, removable by receipt alone. Three
# are whole installer-owned files under ``$GROK_HOME``; ``grok-config`` is
# not a file to delete but a marked block to lift back out, which is why
# ``installer/uninstall.py`` gives it and its Codex twin an arm of their own.
GROK_AUTO_REMOVE_KINDS = frozenset(("grok-skill", "grok-agent", "grok-rules", "grok-config"))
# What the uninstall may remove from the receipt without asking, gated on the
# recorded hash and on the boundary table in ``installer/uninstall.py``, whose
# keys a test holds equal to this set. The three hosts sit here on the same
# terms: role agents for all three, and the two TOML configs lifted key by key
# rather than deleted, since both are files their own CLI writes as well.
#
# Two groups stay off, for reasons that are not "nobody asked":
#
# - ``script``, ``lib``, ``by-name`` and ``host-block`` are all inside
#   ``~/.orchflows``, and so are the retained private runtime and the receipt
#   driving this very cleanup. That tree is handed over as one manual step
#   rather than dismantled file by file while it is still being read.
# - ``claude-config`` is JSON the installer sets one key inside, and there is
#   no lifting one key back out of JSON the way a marked TOML block comes out
#   -- ``render_claude_settings`` has no inverse. Its manual line reports the
#   exact setting instead, which is the undo a user can actually apply.
AUTO_REMOVE_KINDS = frozenset(
    (
        "adapter",
        "prompt",
        "claude-agent",
        "codex-agent",
        "codex-skill",
        "codex-config",
        "frontend-asset",
    )
) | GROK_AUTO_REMOVE_KINDS
CODEX_MAX_THREADS = 20
CODEX_MAX_DEPTH = 1
GROK_MAX_CONCURRENT = 20
# Grok's own cap, not a house choice: a subagent that calls
# ``spawn_subagent`` fails with a depth error, so 1 is the only honest value.
GROK_MAX_DEPTH = 1
CLAUDE_MAX_TOOL_USE_CONCURRENCY = 20
CLAUDE_SETTINGS_SCHEMA = "https://json.schemastore.org/claude-code-settings.json"
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


def _frontend_home() -> Path:
    """The user-owned immutable browser distribution borrowed by projects."""

    return _scope_home("user", None) / "ui"


def _bin_dir(scope: str, project_root: Path | None) -> Path:
    if scope == "user":
        return Path.home() / ".orchflows" / "bin"
    return _require_project_root(project_root) / ".orch" / "bin"


# ``scripts/state_root.py`` owns this pair; the installer runs from the same
# checkout, so it imports the env-var name rather than restating it.
# ``STATE_SINK_SUBPATH`` still mirrors ``state_root.DEFAULT_HOME_SUBPATH``:
# the installer seeds the sink before any receipt exists to resolve it from.
STATE_HOME_ENV_VAR = state_root.ENV_VAR
STATE_SINK_SUBPATH = (".orchflows", "state")


def _state_sink() -> Path:
    """The one sink the user install seeds.

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
    """The durable state directories the user install seeds."""

    if scope != "user":
        raise ValueError("installation supports user scope only")
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

    home = _HOST_ADAPTERS["claude"]["home"]
    override = os.environ.get(home["environment"], "").strip()
    return Path(override).expanduser() if override else Path.home() / home["default"]


def _claude_scope_home(scope: str, project_root: Path | None) -> Path:
    if scope == "user":
        return _claude_user_home()
    return _require_project_root(project_root) / ".claude"


def _claude_md_path(scope: str, project_root: Path | None) -> Path:
    if scope == "user":
        return host_item_path("claude", "instructions", _claude_user_home(), _HOST_ADAPTERS)
    return host_item_path("claude", "instructions", _require_project_root(project_root), _HOST_ADAPTERS)


def _claude_settings_path(scope: str, project_root: Path | None) -> Path:
    return host_item_path("claude", "settings", _claude_scope_home(scope, project_root), _HOST_ADAPTERS)


def _claude_agents_dir(scope: str, project_root: Path | None) -> Path:
    return host_item_path(
        "claude", "role_agent", _claude_scope_home(scope, project_root), _HOST_ADAPTERS,
        profile="{profile}",
    ).parent


def _codex_user_home() -> Path:
    # Codex prompts have no project-local equivalent. Native role agents and
    # config use ``_codex_scope_home`` and therefore follow the selected scope.
    # ``CODEX_HOME`` overrides the ``~/.codex`` default, as the Codex CLI reads it.
    home = _HOST_ADAPTERS["codex"]["home"]
    override = os.environ.get(home["environment"], "").strip()
    return Path(override).expanduser() if override else Path.home() / home["default"]


def _codex_scope_home(scope: str, project_root: Path | None) -> Path:
    if scope == "user":
        return _codex_user_home()
    return _require_project_root(project_root) / ".codex"


def _codex_config_path(scope: str, project_root: Path | None) -> Path:
    return host_item_path("codex", "settings", _codex_scope_home(scope, project_root), _HOST_ADAPTERS)


def _codex_agents_dir(scope: str, project_root: Path | None) -> Path:
    return host_item_path(
        "codex", "role_agent", _codex_scope_home(scope, project_root), _HOST_ADAPTERS,
        agent_type="{agent_type}",
    ).parent


def _codex_agents_path(scope: str, project_root: Path | None) -> Path:
    if scope == "user":
        return host_item_path("codex", "instructions", _codex_user_home(), _HOST_ADAPTERS)
    return host_item_path("codex", "instructions", _require_project_root(project_root), _HOST_ADAPTERS)


def _grok_user_home() -> Path:
    """Grok Build's user config directory, the root of every Grok surface.

    ``GROK_HOME`` overrides the ``~/.grok`` default, as the grok CLI reads it.
    User scope is the whole story here: a project ``.grok/config.toml`` honours
    only ``mcp_servers``, ``plugins``, ``permission`` and ``mcp.max_output_bytes``,
    so nothing this installer writes has a project-local equivalent.
    """

    home = _HOST_ADAPTERS["grok"]["home"]
    override = os.environ.get(home["environment"], "").strip()
    return Path(override).expanduser() if override else Path.home() / home["default"]


def _grok_skills_dir() -> Path:
    return host_item_path(
        "grok", "skill", _grok_user_home(), _HOST_ADAPTERS, name="{name}"
    ).parent.parent


def _grok_agents_dir() -> Path:
    return host_item_path(
        "grok", "role_agent", _grok_user_home(), _HOST_ADAPTERS,
        subagent_type="{subagent_type}",
    ).parent


def _grok_rules_path() -> Path:
    """The one managed file under Grok's instruction root.

    ``$GROK_HOME/rules/*.md`` is loaded as global project instructions, so this
    file is owned whole rather than fenced inside a file the user also writes.
    """

    return host_item_path("grok", "instructions", _grok_user_home(), _HOST_ADAPTERS)


def _grok_config_path() -> Path:
    return host_item_path("grok", "settings", _grok_user_home(), _HOST_ADAPTERS)


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
