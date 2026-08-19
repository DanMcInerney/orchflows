"""Installer plan data and project-plan content helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from .foundation import HOST_BLOCK_TEMPLATE, _bin_dir, _lib_home
from .managed_text import render_host_block
from .packages import template_markers
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
class DayZeroPlan:
    """One day-zero document (``docs/documentation.md`` §6): written only
    where the project holds none, never replaced."""

    dest: Path
    content: str
    kind: str
    label: str


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
    day_zero: list = field(default_factory=list)         # DayZeroPlan — written only when absent
    host_block: ConfigPlan | None = None                 # ~/.orchflows/host-block.md, user scope only
    claude_import: ImportPlan | None = None              # CLAUDE.md import line, user scope only
    warnings: list = field(default_factory=list)         # preflight, informational only
    manage_host_surfaces: bool = True                    # False for thin project plans
    claude_enabled: bool = True                          # user scope: a Claude CLI was detected
    codex_enabled: bool = True                           # user scope: a Codex CLI was detected
    runtime_action: str | None = None                    # create, reuse, repair or refuse


_BUILD_ARTIFACT_SUFFIXES = (".pyc", ".pyo")
_BUILD_ARTIFACT_DIR_NAMES = ("__pycache__",)


def _is_build_artifact(path: Path) -> bool:
    """Stray local bytecode/cache files are never canonical library content."""

    if path.suffix in _BUILD_ARTIFACT_SUFFIXES:
        return True
    return any(part in _BUILD_ARTIFACT_DIR_NAMES for part in path.parts)


def _host_block_content(portable: bool = False) -> tuple[str, str, str]:
    """Render the instruction block against the *user* library paths
    (``~/.orchflows/...``). Both scopes point here: project installs carry
    no library of their own and read the user install instead."""

    lib_home = PurePosixPath("~/.orchflows/lib") if portable else _lib_home("user", None)
    bin_dir = PurePosixPath("~/.orchflows/bin") if portable else _bin_dir("user", None)
    template_text = HOST_BLOCK_TEMPLATE.read_text(encoding="utf-8")
    start_marker, end_marker = template_markers(template_text)
    content = render_host_block(
        template_text,
        bin_dir,
        lib_home / "docs",
        lib_home / "skills",
        lib_home,
        str(private_runtime_python()),
        portable=portable,
    )
    return content, start_marker, end_marker


_DAY_ZERO_VOCABULARY = """# Vocabulary

This project's nouns. Each term is defined once, here, and used with
exactly this meaning everywhere — code, documents, tickets, logs. A
document that needs a different meaning needs a different word.

Sections group by the reader's question; an entry is earned when two
contexts used one word differently. Factory:
{{FACTORY}}.

## Structure

## Work

## Verification
"""

_DAY_ZERO_OWNERSHIP_MAP = """# Architecture

Codemap: where the thing that does X lives, who owns it, and which way
dependencies point. Terms: docs/vocabulary.md. Factory, and the design
law for every document here: {{FACTORY}} (§6 day zero, §7 factories).

## Tiers and ownership

| tier | owner |
|---|---|
| (a directory) | (what it owns, and the tiers it may depend on) |

One row per tier, added when a directory earns an owner, never in advance.
"""


def _day_zero_documents(project_root: Path) -> list:
    """The documents ``docs/documentation.md`` §6 says a project creates on
    day zero, minus the two the instruction blocks already carry (the router)
    and the user install already owns (the state sink).

    Each carries the path of the factory that produced it, rendered against
    the *user* library for ``_host_block_content``'s reason: a project carries
    no library of its own to point at.
    """

    docs_dir = PurePosixPath("~/.orchflows/lib/docs")
    return [
        DayZeroPlan(
            project_root / "docs" / "vocabulary.md",
            _DAY_ZERO_VOCABULARY.replace("{{FACTORY}}", str(docs_dir / "vocabulary-authoring.md")),
            "day-zero",
            "vocabulary skeleton",
        ),
        DayZeroPlan(
            project_root / "ARCHITECTURE.md",
            _DAY_ZERO_OWNERSHIP_MAP.replace("{{FACTORY}}", str(docs_dir / "documentation.md")),
            "day-zero",
            "ownership map skeleton",
        ),
    ]
