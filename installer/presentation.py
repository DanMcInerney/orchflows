"""Human-readable installation plans."""

from __future__ import annotations

from .foundation import (
    _claude_md_path,
    _claude_settings_path,
    _codex_agents_path,
    _codex_config_path,
)
from .models import Plan
from .planning import plan_entry_count
from .runtime import private_runtime_home


def print_plan(plan: Plan, source_commit: str | None) -> None:
    print(f"scope: {plan.scope}")
    if plan.project_root is not None:
        print(f"project root: {plan.project_root}")
    if plan.scope == "user":
        print(f"detected Claude Code CLI: {'yes' if plan.claude_enabled else 'no'}")
        print(f"detected Codex CLI: {'yes' if plan.codex_enabled else 'no'}")
    print(f"source commit: {source_commit or 'unknown'}")
    print(f"library home: {plan.lib_home}")
    print(f"bin dir: {plan.bin_dir}")
    if plan.scope == "user":
        if plan.runtime_action is None:
            print(f"private runtime: not needed {private_runtime_home()}")
        else:
            print(f"private runtime: {plan.runtime_action} {private_runtime_home()}")
    elif plan.runtime_action == "reuse":
        print(f"private runtime: reuse required at {private_runtime_home()} (project scope)")
    else:
        print(
            "private runtime: refuse; project scope requires a healthy user "
            f"runtime at {private_runtime_home()}"
        )
    if plan.frontend_home is not None:
        print(
            f"frontend distribution: {plan.frontend_action} {plan.frontend_home} "
            f"(manifest {plan.frontend_manifest_sha256})"
        )
    print()
    print(f"runtime directories ({len(plan.runtime_dirs)}):")
    for directory in plan.runtime_dirs:
        print(f"  mkdir: {directory}")
    print()
    print(f"library files ({len(plan.lib_copies)}):")
    for pair in plan.lib_copies:
        print(f"  copy: {pair[1]}")
    print()
    print(f"flat name index ({len(plan.by_name)}):")
    for pair in plan.by_name:
        print(f"  write: {pair[0]}")
    print()
    print(f"scripts ({len(plan.scripts)}):")
    for pair in plan.scripts:
        print(f"  install: {pair[1]}")
    print()
    print(f"frontend assets ({len(plan.frontend_assets)}):")
    for pair in plan.frontend_assets:
        print(f"  copy: {pair[1]}")
    if not plan.frontend_assets and plan.frontend_home is not None:
        print(f"  borrow: {plan.frontend_home}")
    print()
    print(f"Claude Code skill adapters ({len(plan.claude_adapters)}):")
    for pair in plan.claude_adapters:
        print(f"  write: {pair[0]}")
    print()
    print(f"Codex prompts ({len(plan.codex_prompts)}):")
    for pair in plan.codex_prompts:
        print(f"  write: {pair[0]}")
    print()
    print(f"Codex redirect skills ({len(plan.codex_skills)}):")
    for pair in plan.codex_skills:
        print(f"  write: {pair[0]}")
    print()
    print(f"Claude Code role agents ({len(plan.claude_agents)}):")
    for pair in plan.claude_agents:
        print(f"  write: {pair[0]}")
    print()
    print(f"Codex role agents ({len(plan.codex_agents)}):")
    for pair in plan.codex_agents:
        print(f"  write: {pair[0]}")
    print()
    print(f"host configuration files ({len(plan.configs)}):")
    for config in plan.configs:
        print(f"  {config.label}: {config.dest}")
    print()
    if plan.host_block is not None:
        print(f"host instruction file: {plan.host_block.dest}")
        print()
    print(f"managed blocks ({len(plan.blocks)}):")
    for block in plan.blocks:
        print(f"  {block.label}: {block.dest}")
    print()
    print(f"day-zero documents ({len(plan.day_zero)}):")
    for document in plan.day_zero:
        print(f"  write if absent: {document.dest} ({document.label})")
    print()
    if plan.claude_import is not None:
        print("managed imports (1):")
        print(f"  {plan.claude_import.label}: {plan.claude_import.dest} -> @{plan.claude_import.import_target}")
        print()
    print(f"receipt: {plan.receipt_path}")
    print()
    print(f"planned entries: {plan_entry_count(plan)}")


def print_summary(plan: Plan) -> None:
    print(f"Installed orchflows at {plan.scope} scope.")
    if plan.frontend_home is not None:
        print(
            f"  frontend:    {plan.frontend_home} "
            f"({plan.frontend_action}; manifest {plan.frontend_manifest_sha256})"
        )
    if not plan.manage_host_surfaces:
        print(f"  instruction blocks: {len(plan.blocks)} written")
        for block in plan.blocks:
            print(f"    {block.label}: {block.dest}")
        print(f"  receipt:     {plan.receipt_path}")
        return
    if plan.scope == "user":
        print(f"  detected Claude Code CLI: {'yes' if plan.claude_enabled else 'no'}")
        print(f"  detected Codex CLI: {'yes' if plan.codex_enabled else 'no'}")
        print(f"  private runtime: {private_runtime_home()}")
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
