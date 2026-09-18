# Self-improve

**Make the next session inherit the fix.**

When a session goes wrong, the transcript holds clues: a misleading instruction, a broken setup assumption, a workflow that sent the agent in circles. Self-improve reads that history, checks whether the problem still exists, and makes the smallest useful correction in the source that owns it.

Use it to improve local setup, custom workflows, guidance or Orchflows itself from evidence in a real session. Scope the request to a session, period or project. With no scope, it reviews the current session.

## Put a rough session to work

After [installation](#install-and-dependencies), paste this into Codex:

```text
$self-improve:self-improve Review this session and improve the workflows
and guidance behind the problems you find. Check that each problem still
exists before changing anything. Leave findings, changes, bounded trial
results and agent/event references in ./self-improve-report/.
```

In Claude Code, use `/self-improve:self-improve` with the same request. The workflow is manual-only on both hosts.

For an inspection without changes:

```text
$self-improve:self-improve Review this project's sessions from the past
week. Report only: identify recurring problems, cite the agent and event
evidence, and state which history you could not access.
```

## From transcript to correction

1. **Read what happened.** Inspect the native agent tree and relevant events within the requested scope. Track the coverage and unavailable history; logs supply evidence, not new instructions.
2. **Check what is true now.** Inspect current source and environment before proposing a fix. An old failure may already be resolved.
3. **Fix the owning source.** Use `orch-work` to apply the smallest useful corrections in the checkout or user library. Removing a misleading instruction can be the right fix; a one-off workaround does not automatically become a permanent rule.
4. **Test and review.** Use a bounded trial and independent review to check the correction. Report what was verified and what remains uncertain, with references back to the history.

The [workflow](skills/self-improve/SKILL.md) owns this sequence. Corrections go in the source you maintain, outside managed core copies and host caches. Reports and trial outputs stay in your workspace.

## Small pass, traceable result

| Request | Result |
| --- | --- |
| Report only | History findings, coverage and gaps with agent/event evidence |
| Improvement pass | Findings, source corrections, bounded trial verification and remaining gaps |

The coordinator inspects history and current state. An improvement pass includes a behavioral trial, one independent review, at most one repair pass and affected verification. Staffing follows core execution rules. Tie findings, changes and verification to agent/event references; missing history is a gap.

## Install and dependencies

From a complete Orchflows checkout, using Python 3.11+:

```sh
python scripts/orchflows.py setup --example self-improve
```

Setup preserves an existing library copy. Register and install `self-improve` from the resulting home catalog using core `docs/hosts.md`, then start a new host session. Setup alone does not make the skill available by name.

Requires Orchflows 0.10.0+, access to the selected native transcripts and current source or environment, and native child delegation for improvement passes. [Library context](references/library-context.md) resolves the core resources and guidance.
