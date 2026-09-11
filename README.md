# orchflows-light

Two delegation skills, composable workflows, and plain Markdown quality standards for Codex and Claude Code. The host runs agents; this library supplies reusable delegation and review guidance. Use ordinary conversation for work that does not benefit from delegation.

| Skill | Action |
| --- | --- |
| [delegate-work](skills/delegate-work/SKILL.md) | Ask a fresh child to make a result. |
| [delegate-review](skills/delegate-review/SKILL.md) | Ask a fresh child who did not make it to review without fixing. |
| [make-and-review](skills/make-and-review/SKILL.md) | Make, review, and allow one repair pass. |
| [compare-approaches](skills/compare-approaches/SKILL.md) | Develop alternatives and compare their actual results. |
| [build-workflow](skills/build-workflow/SKILL.md) | Author a workflow skill, try it on a bounded request, and refine it from observed behavior. |
| [parallel-build](skills/parallel-build/SKILL.md) | Make separable pieces concurrently, then join and review the combined result. |

## Load locally

Keep the complete package together. Substitute your checkout's absolute path below; these are native host commands, with no custom installer.

**Codex:** register the included local marketplace and install the plugin, then start a new session:

```sh
codex plugin marketplace add "/absolute/path/to/orchflows-light"
codex plugin add orchflows-light@orchflows-light-local
```

These commands update native Codex configuration. In CLI/IDE, select a skill with `/skills` or `$orchflows-light:make-and-review`; use the skill picker in the app. See [host details](docs/native-hosts.md) for availability and updates.

**Claude Code:** register the included local marketplace and install for your user:

```sh
claude plugin marketplace add "/absolute/path/to/orchflows-light"
claude plugin install orchflows-light@orchflows-light-local --scope user
```

Start a new session. For development, you can instead load the checkout for one session:

```sh
claude --plugin-dir "/absolute/path/to/orchflows-light"
```

Then try `/orchflows-light:make-and-review Fix the failing export under the Code standard.` Both plugins expose namespaced skill names; invocation syntax differs by host. [Codex packaging](https://developers.openai.com/plugins/build/plugins), [Codex skills](https://developers.openai.com/codex/skills), [Claude plugins](https://code.claude.com/docs/en/plugins).

## Standards

Choose only the useful lenses: [Code](standards/code.md), [Research](standards/research.md), [Writing](standards/writing.md), [Visual design](standards/visual-design.md), and [Data analysis](standards/data-analysis.md). Pass the chosen files to both makers and reviewers. [API code](standards/code/api.md) is a specialized standard with an ordinary parent link; pass Code alongside it.

A new root standard earns a file when it adds a recurring, independent quality lens. A specialized standard adds recurring specificity within an existing lens. A tool or framework name alone earns neither. Keep one-off criteria in the prompt and tool mechanics in a skill or reference.

Write useful making and review criteria. The two headings are a reading convention, with no enforced schema. An `Extends` link is prose: read the parent too. If guidance conflicts, clarify the actual requirement; there is no precedence engine.

## Compose a workflow

Use [build-workflow](skills/build-workflow/SKILL.md) with the recurring request you want to support and a bounded example to try. In this library's checkout, try `$orchflows-light:build-workflow Add a workflow that compares two designs and develops the selected design. Try it on a small example.` In Claude Code, use `/orchflows-light:build-workflow` with the same request. It composes make-and-review, then exercises the resulting skill in a disposable workspace. Edit the source checkout and refresh the installed plugin before trying changes in a new session.

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
