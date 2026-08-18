"""Human-readable installation plans."""

from __future__ import annotations

from .models import Plan
from .planning import plan_entry_count

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
