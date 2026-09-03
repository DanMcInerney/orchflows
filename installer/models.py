"""Installer plan data and project-plan content helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from .foundation import HOST_BLOCK_TEMPLATE, _bin_dir, _lib_home
from .managed_text import render_host_block
from .hosts import load_host_adapters, marker
from .runtime import private_runtime_python

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
    label: str


@dataclass
class Plan:
    lib_home: Path
    scope_home: Path
    bin_dir: Path
    receipt_path: Path
    runtime_dirs: list = field(default_factory=list)
    lib_copies: list = field(default_factory=list)       # (src, dest)
    scripts: list = field(default_factory=list)          # (src, dest)
    frontend_home: Path | None = None
    frontend_assets: list = field(default_factory=list)  # (src, dest)
    frontend_manifest_sha256: str | None = None
    frontend_action: str | None = None                   # create, reuse, repair or refuse
    claude_adapters: list = field(default_factory=list)  # (dest, content) — per-skill SKILL.md stubs
    codex_prompts: list = field(default_factory=list)    # (dest, content)
    codex_skills: list = field(default_factory=list)     # (dest, content) — redirect stubs
    by_name: list = field(default_factory=list)          # (dest, content) — flat name->tiered-source pointers, host-agnostic
    claude_agents: list = field(default_factory=list)    # (dest, content)
    codex_agents: list = field(default_factory=list)     # (dest, content)
    grok_skills: list = field(default_factory=list)      # (dest, content) — $GROK_HOME/skills/<name>/SKILL.md
    grok_agents: list = field(default_factory=list)      # (dest, content)
    configs: list = field(default_factory=list)          # ConfigPlan
    blocks: list = field(default_factory=list)           # BlockPlan — inline marker blocks
    host_block: ConfigPlan | None = None                 # ~/.orchflows/host-block.md
    claude_import: ImportPlan | None = None              # CLAUDE.md import line
    # $GROK_HOME/rules/orchflows.md: the host block as a whole managed file,
    # markers retained. Its own field beside `host_block` rather than a
    # `blocks` entry, because Grok's instruction root is a directory the
    # installer owns a file in, not a file the user owns a block in.
    grok_rules: ConfigPlan | None = None
    # The user's own ring root. Not installed content:
    # `scripts/orchflows_home.py` owns what goes in it, the receipt records
    # none of it, and an uninstall never reaches it.
    home_ring: Path | None = None
    warnings: list = field(default_factory=list)         # preflight, informational only
    manage_host_surfaces: bool = True
    claude_enabled: bool = True                          # a Claude CLI was detected
    codex_enabled: bool = True                           # a Codex CLI was detected
    grok_enabled: bool = True                            # a Grok CLI was detected
    runtime_action: str | None = None                    # create, reuse, repair or refuse


_BUILD_ARTIFACT_SUFFIXES = (".pyc", ".pyo")
_BUILD_ARTIFACT_DIR_NAMES = ("__pycache__",)


def _is_build_artifact(path: Path) -> bool:
    """Stray local bytecode/cache files are never canonical library content."""

    if path.suffix in _BUILD_ARTIFACT_SUFFIXES:
        return True
    return any(part in _BUILD_ARTIFACT_DIR_NAMES for part in path.parts)


def _frontend_manifest(root: Path) -> dict[str, str]:
    """Return the relative-name and byte-hash identity of one distribution."""

    if not root.is_dir():
        return {}
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _frontend_manifest_identity(root: Path) -> str | None:
    manifest = _frontend_manifest(root)
    if not manifest or "index.html" not in manifest:
        return None
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _host_block_content() -> tuple[str, str, str]:
    """Render the instruction block against the installation."""

    lib_home = _lib_home()
    bin_dir = _bin_dir()
    template_text = HOST_BLOCK_TEMPLATE.read_text(encoding="utf-8")
    host_markers = marker("codex", "host_instructions", load_host_adapters())
    start_marker, end_marker = host_markers["start"], host_markers["end"]
    content = render_host_block(
        template_text,
        bin_dir,
        lib_home / "docs",
        lib_home / "skills",
        lib_home,
        str(private_runtime_python()),
    )
    return content, start_marker, end_marker
