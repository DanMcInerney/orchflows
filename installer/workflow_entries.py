"""Installer-owned compatibility entry for the canonical self-improve workflow."""

from pathlib import Path

from .foundation import _claude_user_home, _codex_user_home, _grok_skills_dir
from .hosts import host_item_path, load_host_adapters
from .packages import host_legal_frontmatter, manual_only_frontmatter, split_frontmatter


def self_improve_entry(host: str, workflow_dir: Path) -> str:
    """An inert host spelling; it creates no ring or package identity."""
    frontmatter = (
        "---\nname: orch-self-improve\n"
        "description: Invoke self-improve with the user's focus and timeline.\n---\n"
    )
    head = (
        manual_only_frontmatter(frontmatter, host)
        if host == "claude"
        else host_legal_frontmatter(frontmatter, host)
    )
    return head + (
        "\n`orch-self-improve` invokes the canonical `self-improve` workflow.\n"
        f"Read {workflow_dir / 'SKILL.md'} whole and follow it exactly, keeping "
        "the user's entire request and arguments unchanged, including focus, "
        "timeline, and mode. Invoke only on an explicit user request.\n"
        "Open the frame with `--workflow self-improve`; retain that workflow's "
        "package identity.\n"
    )


def append_self_improve_entries(workflow_dir, claude, prompts, codex, grok):
    """Use ordinary plan lists so receipt, doctor and cleanup own every entry."""
    records = load_host_adapters()
    def destination(host, item, root):
        return host_item_path(host, item, root, records, name="orch-self-improve")

    if claude is not None:
        claude.append((
            destination("claude", "skill", _claude_user_home()),
            self_improve_entry("claude", workflow_dir),
        ))
    if prompts is not None:
        body = split_frontmatter(self_improve_entry("codex", workflow_dir))[1]
        prompts.append((
            destination("codex", "prompt", _codex_user_home()),
            body.strip() + "\n\nUser request: $ARGUMENTS\n",
        ))
    if codex is not None:
        codex.append((
            destination("codex", "skill", _codex_user_home()),
            self_improve_entry("codex", workflow_dir),
        ))
    if grok is not None:
        grok.append((
            destination("grok", "skill", _grok_skills_dir().parent),
            self_improve_entry("grok", workflow_dir),
        ))
