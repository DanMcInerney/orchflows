"""User installation planning."""

from __future__ import annotations

import shutil
from pathlib import Path

from scripts import orchflows_home

from .foundation import (
    CANONICAL_DIRS,
    HOST_ADAPTERS_DIR,
    CLAUDE_ADAPTER_SETS,
    CLAUDE_CLI_CANDIDATES,
    CODEX_CLI_CANDIDATES,
    GROK_CLI_CANDIDATES,
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
    _frontend_home,
    _grok_agents_dir,
    _grok_config_path,
    _grok_rules_path,
    _grok_skills_dir,
    _lib_home,
    _runtime_dirs,
    _scope_home,
)
from .managed_text import (
    grok_skill_text,
    render_claude_settings,
    render_codex_agent_limits,
    render_grok_agent,
    render_grok_subagent_limits,
)
from .models import (
    BlockPlan,
    ConfigPlan,
    ImportPlan,
    Plan,
    _host_block_content,
    _frontend_manifest_identity,
    _is_build_artifact,
)
from .packages import (
    SHEET_MANIFEST_FILE,
    WORKFLOW_SKILL_FILE,
    by_name_pointer_text,
    claude_role_adapter_text,
    codex_role_adapter_body,
    discover_packages,
    discover_sheets,
    discover_workflow_skills,
    frontmatter_field,
    host_legal_frontmatter,
    load_role_profiles,
    manual_only_frontmatter,
    render_claude_agent,
    render_codex_agent,
    split_frontmatter,
    workflow_adapter_body,
)
from .runtime import private_runtime_action
from .planning_support import (
    _frontend_plan,
    _reader_payload_files,
    _script_source,
    _validator_support_copies,
)
from .hosts import host_item_path, load_host_adapters, preflight_instruction_target

def detect_hosts(home: Path | None = None) -> tuple[bool, bool, bool]:
    """Return Claude, Codex and Grok enablement from runnable CLI presence on
    ``PATH``.

    ``home`` remains accepted for caller compatibility, but state/config
    directories under it are deliberately not installation signals. That holds
    for Grok too: ``~/.grok`` -- or a ``GROK_HOME`` pointed anywhere else --
    can outlive the CLI that made it, and the compat directories Grok reads
    are Claude's, so neither says a grok CLI is runnable here.
    """

    del home
    return (
        any(shutil.which(candidate) for candidate in CLAUDE_CLI_CANDIDATES),
        any(shutil.which(candidate) for candidate in CODEX_CLI_CANDIDATES),
        any(shutil.which(candidate) for candidate in GROK_CLI_CANDIDATES),
    )


def _mints_claude_adapter(name: str, claude_adapter_set: str) -> bool:
    """Whether ``name`` gets a Claude skill adapter under this adapter set.

    ``all`` mints one per canonical name; the bounded selector ``four`` mints only
    ``SHARED_ADAPTER_NAMES``, leaving every other name as an explicit
    ``by-name/`` invocation exactly as it already does on Codex. Nothing else in the
    plan moves — the routing benchmark needs the two installs to differ in
    this one surface alone.
    """

    if claude_adapter_set not in CLAUDE_ADAPTER_SETS:
        raise ValueError(f"unknown Claude adapter set: {claude_adapter_set}")
    return claude_adapter_set == "all" or name in SHARED_ADAPTER_NAMES


def _build_user_plan(
    claude_adapter_set: str = "all",
    codex_limits_renderer=render_codex_agent_limits,
    script_name_discoverer=None,
    grok_limits_renderer=render_grok_subagent_limits,
) -> Plan:
    host_adapters = load_host_adapters()
    def item_path(host, item, root, **values):
        return host_item_path(host, item, root, host_adapters, **values)

    lib_home = _lib_home("user", None)
    scope_home = _scope_home("user", None)
    bin_dir = _bin_dir("user", None)
    home = Path.home()
    # Unpacked in full, never sliced: a slice here would discard the third
    # signal silently, and no check would fail. Every patched stand-in must
    # therefore return one member per host, and fails loudly when it does not.
    claude_enabled, codex_enabled, grok_enabled = detect_hosts(home)
    if not (claude_enabled or codex_enabled or grok_enabled):
        return Plan(
            scope="user",
            project_root=None,
            lib_home=lib_home,
            scope_home=scope_home,
            bin_dir=bin_dir,
            receipt_path=scope_home / orchflows_home.RECEIPT_FILENAME,
            warnings=[
                "warning: no Claude Code CLI, Codex CLI or grok CLI was found "
                "on PATH; nothing was installed."
            ],
            claude_enabled=False,
            codex_enabled=False,
            grok_enabled=False,
            runtime_action=None,
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
    for path in sorted(HOST_ADAPTERS_DIR.glob("*.json")):
        lib_copies.append((path, lib_home / path.relative_to(REPO_ROOT)))
    notices = REPO_ROOT / "THIRD_PARTY_NOTICES.md"
    if notices.is_file():
        lib_copies.append((notices, lib_home / notices.name))
    for path in _reader_payload_files():
        if path.is_file():
            lib_copies.append((path, lib_home / path.relative_to(REPO_ROOT)))
    lib_copies.extend(_validator_support_copies(lib_home))
    frontend_home, frontend_identity, frontend_assets, frontend_action = _frontend_plan(
        _frontend_home, _frontend_manifest_identity
    )
    names = script_name_discoverer(REPO_ROOT / "scripts")
    scripts = [
        (_script_source(name), bin_dir / name)
        for name in names
        if _script_source(name).is_file()
    ]

    claude_scope_home = _claude_scope_home("user", None)
    codex_user_home = _codex_user_home()
    claude_adapters = []
    codex_prompts = []
    codex_skills = []
    grok_skills = []
    by_name = []
    profiles = load_role_profiles()
    for skill_md in discover_packages():
        rel = skill_md.relative_to(REPO_ROOT)
        name = skill_md.parent.name
        text = skill_md.read_text(encoding="utf-8")
        frontmatter, body = split_frontmatter(text)
        description = frontmatter_field(frontmatter, "description") or ""
        role = frontmatter_field(frontmatter, "role") or "none"
        lib_skill_md = (lib_home / rel).resolve()
        # Flat, host-agnostic resolution: one deterministic path per canonical
        # name, tier or pack alike, so no agent has to guess a sublayer. The
        # stub only points at the tiered source (never duplicates it), so it
        # carries no relative links to break.
        by_name.append(
            (
                lib_home / "by-name" / name / "SKILL.md",
                by_name_pointer_text(frontmatter, role, lib_skill_md),
            )
        )
        if claude_enabled and _mints_claude_adapter(name, claude_adapter_set):
            claude_adapters.append(
                (
                    item_path("claude", "skill", claude_scope_home, name=name),
                    claude_role_adapter_text(frontmatter, lib_skill_md),
                )
            )
        if codex_enabled:
            codex_body = (
                codex_role_adapter_body(
                    name, role, profiles[f"orch-{role}"], lib_skill_md
                )
                if role in PROFILE_ROLES
                else body.strip() + "\n"
            )
            codex_prompts.append(
                (
                    item_path("codex", "prompt", codex_user_home, name=name),
                    f"# {description}\n\n{codex_body}",
                )
            )
            codex_skills.append(
                (
                    item_path("codex", "skill", codex_user_home, name=name),
                    frontmatter
                    + "\n"
                    + (
                        codex_role_adapter_body(
                            name, role, profiles[f"orch-{role}"], lib_skill_md
                        )
                        if role in PROFILE_ROLES
                        else f"Read {lib_skill_md} and follow it exactly.\n"
                    ),
                )
            )
        if grok_enabled:
            # Every canonical name, not a curated subset: a Grok skill is
            # automatically the slash command `/<name>`, so a name left out
            # here is a name that host cannot invoke at all.
            grok_skills.append(
                (
                    item_path("grok", "skill", _grok_skills_dir().parent, name=name),
                    grok_skill_text(
                        frontmatter,
                        lib_skill_md,
                        profiles[f"orch-{role}"] if role in PROFILE_ROLES else None,
                    ),
                )
            )

    # Workflows are invocable by name, so they get the same name surfaces as
    # skills: a by-name pointer, a Claude adapter stub, a Codex prompt, and
    # — for curated entry points — a Codex redirect stub. Two things differ
    # from a skill, and both are about who runs the body: every workflow
    # surface is manual-invocation-only, so the Claude adapter's frontmatter
    # is forced rather than inherited, and no surface binds a role, because
    # a workflow declares none -- `tools/validate_support/packages.py`'s
    # `validate_role` refuses one in a workflow home, so there is no field
    # here for a host's fork binding to read.
    for workflow_dir, frontmatter, body in discover_workflow_skills():
        name = workflow_dir.name
        description = frontmatter_field(frontmatter, "description") or ""
        lib_workflow_dir = (lib_home / workflow_dir.relative_to(REPO_ROOT)).resolve()
        pointer = (
            frontmatter
            + f"\nRead {lib_workflow_dir / WORKFLOW_SKILL_FILE} and follow it "
            f"exactly. It is the workflow skill at {lib_workflow_dir}, and it "
            "is invoked by name only.\n"
        )
        by_name.append((lib_home / "by-name" / name / "SKILL.md", pointer))
        if claude_enabled and _mints_claude_adapter(name, claude_adapter_set):
            claude_adapters.append(
                (
                    item_path("claude", "skill", claude_scope_home, name=name),
                    manual_only_frontmatter(frontmatter)
                    + workflow_adapter_body(name, lib_workflow_dir, frontmatter),
                )
            )
        if codex_enabled:
            codex_prompts.append(
                (
                    item_path("codex", "prompt", codex_user_home, name=name),
                    f"# {description}\n\n{body.strip()}\n",
                )
            )
            codex_skills.append(
                (
                    item_path("codex", "skill", codex_user_home, name=name),
                    pointer,
                )
            )
        if grok_enabled:
            # The manifest, not the directory: Grok's body is a read
            # instruction, and the manifest is the file that reads.
            grok_skills.append(
                (
                    item_path("grok", "skill", _grok_skills_dir().parent, name=name),
                    grok_skill_text(
                        frontmatter, lib_workflow_dir / WORKFLOW_SKILL_FILE
                    ),
                )
            )

    # A sheet is stamped on a ticket and never invoked, so it gets the one
    # surface a stamped item needs and no host surface at all: the flat
    # pointer, so a child handed the *name* `market-brief` has one
    # deterministic path to read it at, exactly as a pack does. The pointer
    # is named `SHEET.md`, not `SKILL.md` -- the manifest name is what
    # `scripts/rings.py` resolves, and a pointer under the other name would
    # be a second spelling of where a sheet lives.
    for sheet_dir, frontmatter, _body in discover_sheets():
        lib_sheet_dir = (lib_home / sheet_dir.relative_to(REPO_ROOT)).resolve()
        pointer = (
            frontmatter
            + f"\nRead {lib_sheet_dir / SHEET_MANIFEST_FILE} and follow it "
            f"exactly. It is the sheet at {lib_sheet_dir}, stamped on a "
            "ticket beside its pack and never invoked by name.\n"
        )
        by_name.append(
            (lib_home / "by-name" / sheet_dir.name / SHEET_MANIFEST_FILE, pointer)
        )

    claude_agents = []
    codex_agents = []
    grok_agents = []
    for name in (f"orch-{role}" for role in PROFILE_ROLES):
        profile = profiles[name]
        if claude_enabled:
            claude_agents.append(
                (
                    item_path("claude", "role_agent", claude_scope_home, profile=name),
                    render_claude_agent(name, profile),
                )
            )
        if codex_enabled:
            codex_agent_type = profile["codex"]["agent_type"]
            codex_agents.append(
                (
                    item_path("codex", "role_agent", codex_user_home, agent_type=codex_agent_type),
                    render_codex_agent(name, profile),
                )
            )
        if grok_enabled:
            # The rendered item template names files by native subagent_type.
            grok_agents.append(
                (
                    item_path("grok", "role_agent", _grok_agents_dir().parent,
                              subagent_type=profile["grok"]["subagent_type"]),
                    render_grok_agent(name, profile),
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
    if grok_enabled:
        grok_config_path = _grok_config_path()
        grok_config_text = grok_config_path.read_text(encoding="utf-8") if grok_config_path.is_file() else ""
        grok_config, grok_details = grok_limits_renderer(grok_config_text)
        if not grok_details["toml_checked"]:
            warnings.append(
                "warning: this interpreter has no tomllib (Python < 3.11), so "
                f"{grok_config_path} was merged without a TOML parse check."
            )
        configs.append(
            ConfigPlan(
                grok_config_path,
                grok_config,
                "grok-config",
                "Grok subagent limits",
                grok_details,
            )
        )

    host_block, start_marker, end_marker = _host_block_content()
    blocks = []
    host_block_plan = None
    claude_import_plan = None
    grok_rules_plan = None
    if claude_enabled:
        host_block_path = scope_home / "host-block.md"
        claude_md_path = _claude_md_path("user", None)
        preflight_instruction_target("claude", claude_md_path, host_block,
                                     host_block_path.resolve(), host_adapters)
        host_block_plan = ConfigPlan(host_block_path, host_block, "host-block", "Host instruction block")
        claude_import_plan = ImportPlan(
            claude_md_path,
            host_block_path.resolve(),
            start_marker,
            end_marker,
            "Claude Code instruction import",
        )
    if codex_enabled:
        codex_agents_path = _codex_agents_path("user", None)
        preflight_instruction_target("codex", codex_agents_path, host_block,
                                     adapters=host_adapters)
        blocks.append(
            BlockPlan(
                codex_agents_path,
                host_block,
                start_marker,
                end_marker,
                "Codex AGENTS.md instruction block",
            )
        )
    if grok_enabled:
        # The whole file, markers and all. `$GROK_HOME/rules/*.md` loads as
        # global project instruction, so the installer owns one file there
        # rather than upserting a block into an AGENTS.md the user may own --
        # and the markers stay inside it, so identity and uninstall still read
        # the same way they do on the other two hosts.
        grok_rules_plan = ConfigPlan(
            _grok_rules_path(), host_block, "grok-rules", "Grok instruction file"
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
        frontend_home=frontend_home,
        frontend_assets=frontend_assets,
        frontend_manifest_sha256=frontend_identity,
        frontend_action=frontend_action,
        claude_adapters=claude_adapters,
        codex_prompts=codex_prompts,
        codex_skills=codex_skills,
        by_name=by_name,
        claude_agents=claude_agents,
        codex_agents=codex_agents,
        grok_skills=grok_skills,
        grok_agents=grok_agents,
        configs=configs,
        blocks=blocks,
        host_block=host_block_plan,
        claude_import=claude_import_plan,
        grok_rules=grok_rules_plan,
        receipt_path=scope_home / orchflows_home.RECEIPT_FILENAME,
        home_ring=scope_home,
        warnings=warnings,
        claude_enabled=claude_enabled,
        codex_enabled=codex_enabled,
        grok_enabled=grok_enabled,
        runtime_action=private_runtime_action(),
    )


def build_plan(
    scope: str,
    project_root: Path | None,
    claude_adapter_set: str = "all",
    codex_limits_renderer=render_codex_agent_limits,
    script_name_discoverer=None,
    grok_limits_renderer=render_grok_subagent_limits,
) -> Plan:
    if scope != "user":
        raise ValueError("installation supports user scope only")
    return _build_user_plan(
        claude_adapter_set,
        codex_limits_renderer,
        script_name_discoverer,
        grok_limits_renderer,
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
        + len(plan.frontend_assets)
        + len(plan.claude_adapters)
        + len(plan.codex_prompts)
        + len(plan.codex_skills)
        + len(plan.by_name)
        + len(plan.claude_agents)
        + len(plan.codex_agents)
        + len(plan.grok_skills)
        + len(plan.grok_agents)
        + len(plan.configs)
        + len(plan.blocks)
        + (1 if plan.host_block is not None else 0)
        + (1 if plan.claude_import is not None else 0)
        + (1 if plan.grok_rules is not None else 0)
        + (1 if plan.home_ring is not None else 0)
        + (
            1
            if plan.scope == "user" and plan.runtime_action in ("create", "repair")
            else 0
        )
    )
