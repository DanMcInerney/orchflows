"""User and project installation planning."""

from __future__ import annotations

import shutil
from pathlib import Path

from .foundation import (
    CANONICAL_DIRS,
    CLAUDE_ADAPTER_SETS,
    CLAUDE_CLI_CANDIDATES,
    CODEX_CLI_CANDIDATES,
    CODEX_SKILL_REDIRECT_NAMES,
    PROFILE_ROLES,
    REPO_ROOT,
    SHARED_ADAPTER_NAMES,
    _bin_dir,
    _claude_agents_dir,
    _claude_md_path,
    _claude_scope_home,
    _claude_settings_path,
    _codex_agents_dir,
    _codex_agents_path,
    _codex_config_path,
    _codex_hooks_warnings,
    _codex_user_home,
    _lib_home,
    _require_project_root,
    _runtime_dirs,
    _scope_home,
)
from .managed_text import render_claude_settings, render_codex_agent_limits
from .models import (
    BlockPlan,
    ConfigPlan,
    ImportPlan,
    Plan,
    _day_zero_documents,
    _host_block_content,
    _is_build_artifact,
)
from .packages import (
    TEMPLATE_MANIFEST,
    discover_packages,
    discover_templates,
    frontmatter_field,
    host_legal_frontmatter,
    load_role_profiles,
    render_claude_agent,
    render_codex_agent,
    split_frontmatter,
    template_adapter_body,
)

def _build_project_plan(project_root: Path) -> Plan:
    """Thin stub: only the two managed instruction blocks plus a minimal
    receipt. No lib copy, no runtime dirs, no ``.claude``/``.codex`` writes —
    a project install borrows the user install for everything else."""

    host_block, start_marker, end_marker = _host_block_content()
    blocks = [
        BlockPlan(
            _claude_md_path("project", project_root),
            host_block,
            start_marker,
            end_marker,
            "Claude Code instruction block",
        ),
        BlockPlan(
            _codex_agents_path("project", project_root),
            host_block,
            start_marker,
            end_marker,
            "Codex AGENTS.md instruction block",
        ),
    ]
    scope_home = _scope_home("project", project_root)
    return Plan(
        scope="project",
        project_root=project_root,
        lib_home=_lib_home("project", project_root),
        scope_home=scope_home,
        bin_dir=_bin_dir("project", project_root),
        blocks=blocks,
        day_zero=_day_zero_documents(project_root),
        receipt_path=scope_home / "receipt.json",
        manage_host_surfaces=False,
    )


def detect_hosts(home: Path | None = None) -> tuple[bool, bool]:
    """Return host enablement from runnable CLI presence on ``PATH``.

    ``home`` remains accepted for caller compatibility, but state/config
    directories under it are deliberately not installation signals.
    """

    del home
    return (
        any(shutil.which(candidate) for candidate in CLAUDE_CLI_CANDIDATES),
        any(shutil.which(candidate) for candidate in CODEX_CLI_CANDIDATES),
    )


def _mints_claude_adapter(name: str, claude_adapter_set: str) -> bool:
    """Whether ``name`` gets a Claude skill adapter under this adapter set.

    ``all`` mints one per canonical name; ``four`` mints only
    ``SHARED_ADAPTER_NAMES``, leaving every other name to resolve at
    ``by-name/`` exactly as it already does on Codex. Nothing else in the
    plan moves — the routing benchmark SPEC §7.2 gates the decision on
    needs the two installs to differ in this one surface alone.
    """

    if claude_adapter_set not in CLAUDE_ADAPTER_SETS:
        raise ValueError(f"unknown Claude adapter set: {claude_adapter_set}")
    return claude_adapter_set == "all" or name in SHARED_ADAPTER_NAMES


def _build_user_plan(
    claude_adapter_set: str = "all",
    codex_limits_renderer=render_codex_agent_limits,
    script_name_discoverer=None,
) -> Plan:
    lib_home = _lib_home("user", None)
    scope_home = _scope_home("user", None)
    bin_dir = _bin_dir("user", None)
    home = Path.home()
    claude_enabled, codex_enabled = detect_hosts(home)
    if not claude_enabled and not codex_enabled:
        return Plan(
            scope="user",
            project_root=None,
            lib_home=lib_home,
            scope_home=scope_home,
            bin_dir=bin_dir,
            receipt_path=scope_home / "receipt.json",
            warnings=[
                "warning: neither a Claude Code CLI nor a Codex CLI was found "
                "on PATH; nothing was installed."
            ],
            claude_enabled=False,
            codex_enabled=False,
        )

    lib_copies = []
    for name in CANONICAL_DIRS:
        src_dir = REPO_ROOT / name
        if not src_dir.is_dir():
            continue
        for path in sorted(src_dir.rglob("*")):
            if path.is_file() and not _is_build_artifact(path):
                rel = path.relative_to(REPO_ROOT)
                lib_copies.append((path, lib_home / rel))

    scripts = [
        (REPO_ROOT / "scripts" / name, bin_dir / name)
        for name in script_name_discoverer(REPO_ROOT / "scripts")
    ]

    claude_scope_home = _claude_scope_home("user", None)
    codex_user_home = _codex_user_home()
    claude_adapters = []
    codex_prompts = []
    codex_skills = []
    by_name = []
    for skill_md in discover_packages():
        rel = skill_md.relative_to(REPO_ROOT)
        name = skill_md.parent.name
        text = skill_md.read_text(encoding="utf-8")
        frontmatter, body = split_frontmatter(text)
        description = frontmatter_field(frontmatter, "description") or ""
        lib_skill_md = (lib_home / rel).resolve()
        # Flat, host-agnostic resolution: one deterministic path per canonical
        # name, tier or pack alike, so no agent has to guess a sublayer. The
        # stub only points at the tiered source (never duplicates it), so it
        # carries no relative links to break.
        by_name.append(
            (
                lib_home / "by-name" / name / "SKILL.md",
                frontmatter + f"\nRead {lib_skill_md} and follow it exactly.\n",
            )
        )
        if claude_enabled and _mints_claude_adapter(name, claude_adapter_set):
            claude_adapters.append(
                (claude_scope_home / "skills" / name / "SKILL.md", host_legal_frontmatter(frontmatter) + f"@{lib_skill_md}\n")
            )
        if codex_enabled:
            codex_prompts.append(
                (codex_user_home / "prompts" / f"{name}.md", f"# {description}\n\n{body.strip()}\n")
            )
            if name in CODEX_SKILL_REDIRECT_NAMES:
                codex_skills.append(
                    (
                        codex_user_home / "skills" / name / "SKILL.md",
                        frontmatter + f"\nRead {lib_skill_md} and follow it exactly.\n",
                    )
                )

    # Compositions are invocable by name, so they get the same name surfaces
    # as skills: a by-name pointer, a Claude adapter stub, a Codex prompt,
    # and — for curated entry points — a Codex redirect stub. Uniform across
    # entry values: routed and named alike. What differs from a skill is only
    # what a stub can point at: a template is a directory, so the pointer
    # names the directory and the adapter carries the two commands that run
    # it instead of an ``@``-include of a body that does not exist.
    for template_dir, frontmatter, body in discover_templates():
        name = template_dir.name
        description = frontmatter_field(frontmatter, "description") or ""
        lib_template_dir = (lib_home / template_dir.relative_to(REPO_ROOT)).resolve()
        pointer = (
            frontmatter
            + f"\nRead {lib_template_dir / TEMPLATE_MANIFEST} and follow it "
            f"exactly. It is the manifest of the ticket-set template at "
            f"{lib_template_dir}.\n"
        )
        by_name.append((lib_home / "by-name" / name / "SKILL.md", pointer))
        if claude_enabled and _mints_claude_adapter(name, claude_adapter_set):
            claude_adapters.append(
                (
                    claude_scope_home / "skills" / name / "SKILL.md",
                    host_legal_frontmatter(frontmatter)
                    + template_adapter_body(name, lib_template_dir, frontmatter),
                )
            )
        if codex_enabled:
            codex_prompts.append(
                (codex_user_home / "prompts" / f"{name}.md", f"# {description}\n\n{body.strip()}\n")
            )
            if name in CODEX_SKILL_REDIRECT_NAMES:
                codex_skills.append(
                    (codex_user_home / "skills" / name / "SKILL.md", pointer)
                )

    profiles = load_role_profiles()
    claude_agents = []
    codex_agents = []
    for name in (f"orch-{role}" for role in PROFILE_ROLES):
        profile = profiles[name]
        if claude_enabled:
            claude_agents.append(
                (_claude_agents_dir("user", None) / f"{name}.md", render_claude_agent(name, profile))
            )
        if codex_enabled:
            codex_agent_type = profile["codex"]["agent_type"]
            codex_agents.append(
                (
                    _codex_agents_dir("user", None) / f"{codex_agent_type}.toml",
                    render_codex_agent(name, profile),
                )
            )

    configs = []
    warnings = _codex_hooks_warnings(codex_user_home) if codex_enabled else []
    if claude_enabled:
        claude_settings_path = _claude_settings_path("user", None)
        claude_settings_text = (
            claude_settings_path.read_text(encoding="utf-8") if claude_settings_path.is_file() else ""
        )
        claude_settings, claude_details = render_claude_settings(claude_settings_text)
        configs.append(
            ConfigPlan(
                claude_settings_path,
                claude_settings,
                "claude-config",
                "Claude Code concurrency settings",
                claude_details,
            )
        )
    if codex_enabled:
        codex_config_path = _codex_config_path("user", None)
        codex_config_text = codex_config_path.read_text(encoding="utf-8") if codex_config_path.is_file() else ""
        codex_config, codex_details = codex_limits_renderer(codex_config_text)
        if not codex_details["toml_checked"]:
            warnings.append(
                "warning: this interpreter has no tomllib (Python < 3.11), so "
                f"{codex_config_path} was merged without a TOML parse check."
            )
        configs.append(
            ConfigPlan(
                codex_config_path,
                codex_config,
                "codex-config",
                "Codex agent limits",
                codex_details,
            )
        )

    host_block, start_marker, end_marker = _host_block_content()
    blocks = []
    host_block_plan = None
    claude_import_plan = None
    if claude_enabled:
        host_block_path = scope_home / "host-block.md"
        host_block_plan = ConfigPlan(host_block_path, host_block, "host-block", "Host instruction block")
        claude_import_plan = ImportPlan(
            _claude_md_path("user", None),
            host_block_path.resolve(),
            start_marker,
            end_marker,
            "Claude Code instruction import",
        )
    if codex_enabled:
        blocks.append(
            BlockPlan(
                _codex_agents_path("user", None),
                host_block,
                start_marker,
                end_marker,
                "Codex AGENTS.md instruction block",
            )
        )

    return Plan(
        scope="user",
        project_root=None,
        lib_home=lib_home,
        scope_home=scope_home,
        bin_dir=bin_dir,
        runtime_dirs=_runtime_dirs("user", None),
        lib_copies=lib_copies,
        scripts=scripts,
        claude_adapters=claude_adapters,
        codex_prompts=codex_prompts,
        codex_skills=codex_skills,
        by_name=by_name,
        claude_agents=claude_agents,
        codex_agents=codex_agents,
        configs=configs,
        blocks=blocks,
        host_block=host_block_plan,
        claude_import=claude_import_plan,
        receipt_path=scope_home / "receipt.json",
        warnings=warnings,
        claude_enabled=claude_enabled,
        codex_enabled=codex_enabled,
    )


def build_plan(
    scope: str,
    project_root: Path | None,
    claude_adapter_set: str = "all",
    codex_limits_renderer=render_codex_agent_limits,
    script_name_discoverer=None,
) -> Plan:
    if scope == "project":
        # A project install writes no host skill surfaces at all, so the
        # adapter set has nothing to select.
        return _build_project_plan(_require_project_root(project_root))
    return _build_user_plan(
        claude_adapter_set, codex_limits_renderer, script_name_discoverer
    )


def plan_entry_count(plan: Plan) -> int:
    """Every directory, file and managed edit the plan would produce.

    ``--dry-run`` prints this so a green run states whether it planned the
    install or planned nothing at all; the bare 0 it used to return read the
    same either way.
    """

    return (
        len(plan.runtime_dirs)
        + len(plan.lib_copies)
        + len(plan.scripts)
        + len(plan.claude_adapters)
        + len(plan.codex_prompts)
        + len(plan.codex_skills)
        + len(plan.by_name)
        + len(plan.claude_agents)
        + len(plan.codex_agents)
        + len(plan.configs)
        + len(plan.blocks)
        + len(plan.day_zero)
        + (1 if plan.host_block is not None else 0)
        + (1 if plan.claude_import is not None else 0)
    )


