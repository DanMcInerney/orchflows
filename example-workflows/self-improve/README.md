# Self-improve

`/self-improve` reviews native agent history to improve local setup, custom workflows, guidance or Orchflows itself. Scope it to a session, period or project; by default it reviews the current session.

> /self-improve Review this session and improve the workflows and guidance behind the problems you find.

The [workflow](skills/self-improve/SKILL.md) checks whether observed failures still exist in the current source or environment before making the smallest useful correction. An improvement pass uses one `orch-work` maker and one independent `orch-review` reviewer, with a bounded trial. A report-only request stops after history inspection and uses no children. Findings, changes and verification refer back to agent and event evidence; unavailable history remains a gap.

## Install and dependencies

From a complete Orchflows checkout, run `python scripts/orchflows.py setup --example self-improve` with Python 3.11+. Setup preserves an existing library. Register and install `self-improve` from the resulting home catalog using core `docs/hosts.md`; setup alone does not make it available by name. The workflow is manual-only on Codex and Claude Code. Its native names are `$self-improve:self-improve` in Codex and `/self-improve:self-improve` in Claude Code.

Requires Orchflows 0.7.0+, access to the selected native transcripts and current source or environment, and native child delegation for improvement passes. [Library context](references/library-context.md) resolves the core resources and guidance. Corrections belong in the owning checkout or user library; keep reports and trial outputs in the caller's workspace.
