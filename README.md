# orchflows-light

Two delegation skills, two example workflows, and plain Markdown quality standards for Codex and Claude Code. The host runs agents; this library supplies reusable delegation and review guidance. Use ordinary conversation for work that does not benefit from delegation.

| Skill | Action |
| --- | --- |
| [delegate-work](skills/delegate-work/SKILL.md) | Ask a fresh child to make a result. |
| [delegate-review](skills/delegate-review/SKILL.md) | Ask a fresh child who did not make it to review without fixing. |
| [make-and-review](skills/make-and-review/SKILL.md) | Make, review, and allow one repair pass. |
| [compare-approaches](skills/compare-approaches/SKILL.md) | Develop alternatives and compare their actual results. |

## Load locally

Keep the complete package together. Substitute your checkout's absolute path below; these are native host commands, with no custom installer.

**Codex:** register the included local marketplace and install the plugin, then start a new session:

```sh
codex plugin marketplace add "/absolute/path/to/orchflows-light"
codex plugin add orchflows-light@orchflows-light-local
```

These commands update native Codex configuration. In CLI/IDE, select a skill with `/skills` or `$make-and-review`; use the skill picker in the app. See [host details](docs/native-hosts.md) for availability and updates.

**Claude Code:** load for this session without installing:

```sh
claude --plugin-dir "/absolute/path/to/orchflows-light"
```

Then try `/orchflows-light:make-and-review Fix the failing export under the Code standard.` Claude namespaces plugin skills; Codex uses its native skill selection. [Codex packaging](https://developers.openai.com/plugins/build/plugins), [Codex skills](https://developers.openai.com/codex/skills), [Claude plugins](https://code.claude.com/docs/en/plugins).

## Standards

Choose only the useful lenses: [Code](standards/code.md), [Research](standards/research.md), [Writing](standards/writing.md), [Visual design](standards/visual-design.md), and [Data analysis](standards/data-analysis.md). Pass the chosen files to both makers and reviewers. [API code](standards/code/api.md) is a specialized standard with an ordinary parent link; pass Code alongside it.

A new root standard earns a file when it adds a recurring, independent quality lens. A specialized standard adds recurring specificity within an existing lens. A tool or framework name alone earns neither. Keep one-off criteria in the prompt and tool mechanics in a skill or reference.

Write useful making and review criteria. The two headings are a reading convention, with no enforced schema. An `Extends` link is prose: read the parent too. If guidance conflicts, clarify the actual requirement; there is no precedence engine.

## Compose a workflow

Add a native `skills/<action>/SKILL.md` with a name, description and useful prose. For example, a new `prepare-proposal` skill in this package could contain:

```markdown
---
name: prepare-proposal
description: Compare proposed approaches and develop a reviewed proposal.
---

Load [compare-approaches](../compare-approaches/SKILL.md) for the proposed
alternatives. Load [make-and-review](../make-and-review/SKILL.md) to develop
the selected approach. Use [delegate-work](../delegate-work/SKILL.md) to
join the chosen contributions into one proposal, then
[delegate-review](../delegate-review/SKILL.md) to review the combined work.
Use delegate-work with [Writing](../../standards/writing.md) to write the
final report from the reviewed proposal and its remaining limitations.
```

Load composed skills in the current orchestrator by default. Explicitly delegate orchestration when useful and supported by the host. Children can use ordinary capability skills.

A workflow folder can carry useful `scripts/`, `references/` and `assets/`; add them when the work needs them. Resolve their paths from the actual loaded skill file, including installed cache copies, and name required dependencies in that skill. Keep output in the task workspace. [Native host guidance](docs/native-hosts.md) covers package paths, worktrees, model settings and capability limits.
