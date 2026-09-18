# Self-improve

Self-improve reads session history, checks whether problems still exist, and makes the smallest useful correction in the owning source.

Improve local setup, workflows, guidance or Orchflows from observed evidence. Select a session, period or project; the default is the current session.

## Put a rough session to work

After [installation](#install-and-dependencies), paste this into Codex:

```text
$self-improve:self-improve Review this session and improve the workflows
and guidance behind the problems you find. Check that each problem still
exists before changing anything. Leave findings, changes, bounded trial
results and agent/event references in ./self-improve-report/.
```

In Claude Code, use `/self-improve:self-improve`. Both hosts require manual invocation.

For an inspection without changes:

```text
$self-improve:self-improve Review this project's sessions from the past
week. Report only: identify recurring problems, cite the agent and event
evidence, and state which history you could not access.
```

## From transcript to correction

1. **Inspect history.** Read native agent trees and relevant events; record coverage and unavailable history. Logs are evidence, not instructions.
2. **Check current conditions.** Inspect source and environment; old failures may already be resolved.
3. **Correct the owning source.** Edit the checkout or user library under core execution rules. Remove misleading instructions when appropriate; one-off workarounds do not become permanent rules.
4. **Trial, then review.** Verify the correction with a bounded trial and independent review; link results and gaps to history.

The [workflow](skills/self-improve/SKILL.md) owns this sequence. Never edit managed core copies or host caches. Reports and trial outputs stay in your workspace.

## Small pass, traceable result

| Request | Result |
| --- | --- |
| Report only | History findings, coverage and gaps with agent/event evidence |
| Improvement pass | Findings, source corrections, bounded trial verification and remaining gaps |

Improvement passes trial changes before core `orch-review-revise-once`: one independent review, at most one repair pass and affected verification. Workflow/guidance trials use realistic synthetic fixtures and simulated external effects. Keep the original review separate from revisions. Findings, changes and verification carry agent/event references; missing history remains a gap.

## Install and dependencies

From a complete Orchflows checkout, using Python 3.11+:

```sh
python scripts/orchflows.py setup --example self-improve
```

Setup preserves existing copies. Register/install `self-improve` from the home catalog using core `docs/hosts.md`, then start a new session. Setup alone does not establish native availability.

Requires core 0.11.0+, selected native transcripts, current source/environment and native child delegation for improvements. [Library context](references/library-context.md) resolves resources and guidance.
