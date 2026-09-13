# Orchflows guidance review — 12 September 2026

Historical research and recommendations, not current instructions. Current contracts: [architecture](../docs/architecture.md).

**Keep the Make/Review structure, but tighten what it contains.** The strongest candidates for deletion are generic competence reminders and repeated process instructions. The strongest candidates for retention are consequential distinctions, explicit preferences and criteria that make a result assessable. A mandatory vocabulary section is not supported by the evidence. Your concern about `principles.md` is justified: my previous draft still includes general code advice that does not explain an Orchflows design decision.

These are evidence-informed recommendations, not demonstrated improvements to Orchflows. No comparative runs of our guidance were performed. Neither popularity nor a literature review can establish that we have the “best” instructions.

**What I reviewed**

All five default domains and the API specialization: `code`, `research`, `writing`, `visual-design`, `data-analysis`, and `code.api`. I read the renamed guidance at commit `657fddb` on `codex/simplify-ownership`; its six guidance files match `claude/simplify-guidance-and-core`. This worktree remains at `6f12494`, with the older `standards` layout. The principles assessment uses the local, uncommitted draft from our preceding work. The library comparisons use pinned revisions linked below. [Reviewed guidance tree](https://github.com/DanMcInerney/orchflows-light/tree/657fddb8134744581037b69714d639af0bbb65ce/guidance)

Four investigators covered the named libraries, expert/model advice and empirical studies; I audited our files and combined the evidence. The research distinguishes provider observations, controlled studies, practitioner experience and my recommendations. The report does not change the guidance or principles.

**What the latest models change**

OpenAI's exact **GPT-6 Astra** guidance says stronger instruction following makes conflicting skills and `AGENTS.md` rules more consequential. It recommends auditing them. It also identifies excessive testing on smaller changes, detailed/formulaic writing, and insufficient delegation as behaviors worth calibrating. This supports concise preferences and bounded verification, while placing delegation policy in the workflow that owns it. [Astra prompting guidance](https://developers.openai.com/api/docs/guides/latest-model#prompting-best-practices)

Anthropic's exact **Fable 5.1** guide reports unrequested additions and excessive permanent tests; scope instructions reduce these without measurable task-success loss in its evaluation. It also identifies dense prose, less retrieval at low effort, and unnecessary whole-file rewrites. Existing Fable 5 prompts generally transfer: the advice is to address observed behavior, rather than reset every prompt automatically. [Fable 5.1 prompting guidance](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1)

My implication for our files: replace open-ended encouragement to do more with criteria for sufficient work. Keep a durable preference such as “verification should match the changed behavior and its consequences.” Model-specific effort settings, batching nudges and editing-tool remedies belong in revisitable host/model guidance, not every domain document.

The deletion trend has a substantial first-party basis. On July 24, Thariq Shihipar reported that Anthropic removed over 80% of Claude Code's system prompt for Opus 5 and Fable 5 without measurable loss on its coding evaluations. Overlapping instructions and newly unnecessary constraints were central problems. This was a prompt reduction in a particular harness, not removal of every source of context, and not an evaluation of our six files. [Anthropic's account](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models)

**What the research actually establishes**

| Evidence | Result | Limit on the conclusion |
| --- | --- | --- |
| *Evaluating AGENTS.md*, June revision | Generated context did not significantly improve accuracy and increased costs by roughly 20–23%. Developer files performed better than generated files; their improvement over no file was not statistically significant. | Python coding tasks, older models, one completion per condition. These were repository context files, not selectively loaded domain criteria. It supports auditing unnecessary actions and redundancy, not claiming that deletion reliably improves correctness. [Paper v2](https://arxiv.org/html/2602.11988v2) |
| *SkillsBench*, June revision | Curated skill bundles increased mean pass rate from 33.9% to 50.5% across 87 tasks and 18 model/harness configurations. | Bundles include scripts, examples and specialist knowledge. Tasks without measurable separation were rejected during construction. Shorter and longer bundles served different tasks; this was not a controlled test of shortening the same prose. Neither named latest model was tested. [Paper v4](https://arxiv.org/html/2602.12670v4) |
| *SWE-Skills-Bench* | Haiku 4.5 improved from 89.8% to 91.0%, with 10.5% more tokens; most skills showed no pass-rate change. | Strong ceiling effects and one model. Version-mismatched templates sometimes hurt, supporting caution about frozen recipes rather than blanket deletion of criteria. [Paper](https://arxiv.org/html/2603.15401v1) |

The evidence makes the **marginal value of the actual loaded instruction** the right question. An instruction can be short and still cause unnecessary work. A longer definition can be useful if it prevents a consequential misunderstanding. File length alone is a weak proxy.

**What to borrow from the popular libraries**

These are the three substantial libraries you named, not an exhaustive popularity ranking. Each comparison concerns the linked version and the author's chosen goals; adoption does not establish prompting effectiveness.

| Library | Useful contribution | What I would leave out of general guidance |
| --- | --- | --- |
| **Garry Tan's gstack**, September 9 snapshot | Its review criteria distinguish missing behavior from unrequested structure. This captures “complete the request” and “avoid speculative machinery” more clearly than a demand for fewer lines. | Its large review skill also owns specialist dispatch, setup, repair policy and many operational conventions. Those are workflow decisions. Its house philosophy deliberately favors ambitious completeness; Orchflows can make different tradeoffs. [Checklist](https://github.com/garrytan/gstack/blob/71f6048e8ada25180e61438abc1d98cb151fe9a7/review/checklist.md), [review workflow](https://github.com/garrytan/gstack/blob/71f6048e8ada25180e61438abc1d98cb151fe9a7/review/SKILL.md) |
| **Matt Pocock's skills**, September 4 snapshot | `writing-for-agents` treats redundancy as model-relative: compare behavior with the default, then delete ineffective sentences. It distinguishes reference material from procedures and gives each meaning one owner. | Its theory that “leading words” compactly activate useful behavior is a plausible author rationale, not a controlled result. Escalating adjectives to force greater effort could work against our scope and speed goals. [Authoring guidance](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/productivity/writing-for-agents/SKILL.md) |
| **Jesse Vincent's Superpowers**, August 12 snapshot | Its authoring guidance uses fresh-context samples and a no-guidance control. It distinguishes output-shape failures from skipped rules, and reports that different wording works for each. | Its discipline enforcement, per-task review structure and repair machinery encode a particular development process. Compliance with that process is not equivalent to better finished work. Borrow the comparative testing idea, not the whole procedure. [Authoring guidance](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/writing-skills/SKILL.md), [subagent workflow](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/subagent-driven-development/SKILL.md) |

An actual expert instruction file is also instructive: Pocock's `CLAUDE.md` primarily records repository organization, packaging rules, commands and pointers. His `AGENTS.md` points to that owner. It is evidence for local architectural knowledge rather than another generic clean-code essay. [Pocock's CLAUDE.md](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/CLAUDE.md)

The firsthand accounts are mixed. Jeroen Vonk proposes deleting accumulated behavioral corrections while retaining project facts; his article describes a proposed week-long experiment, not a completed causal result. Alexander Thalhammer's September-updated account still credits shared style guidance and `AGENTS.md` with making subagent output fit his Angular project, while recommending a review after model upgrades. Both support deliberate maintenance. [Vonk](https://sparkone.nl/en/blog/delete-your-claude-md-every-six-months/), [Thalhammer](https://www.angulararchitects.io/blog/ae-summer-2026-update-for-angular/)

Relevant X posts were discovered, including [Lance Martin's prompt-audit post](https://x.com/RLanceMartin/status/2095170001175199771) and [Om Patel's clean-install demonstration](https://x.com/om_patel5/status/2094969981687517694), but direct retrieval failed. I have not treated indexed excerpts as verified full posts or established a broad X consensus. A successful clean-install demonstration would also need a matched comparison to establish that deletion caused improvement.

**Vocabulary: useful distinctions, optional section**

I would **not add a Vocabulary section to every default domain**. Consistent terminology is worthwhile; the section heading has no demonstrated special value. Anthropic recommends consistent terms while assuming Claude already understands ordinary concepts. [Skill-authoring guidance](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)

There are three different cases:

| Kind of vocabulary | Example | Recommendation |
| --- | --- | --- |
| Familiar professional language | Regression, hierarchy, evidence | Use the term directly unless its intended meaning is narrower than usual. Avoid a miniature textbook. |
| Local meaning or consequential distinction | Loading a skill versus launching an agent; a review finding versus a style preference | Define it once where the behavior is owned. Ensure all relevant agents receive that definition. |
| Contract between outputs | Status values, field names, metric units, what one row represents | Put the exact definition in the shared handoff or task context. This directly addresses whether separate outputs can fit together. |

Pocock's project glossary format expressly excludes general programming concepts. His codebase-design glossary serves a different purpose: it defines a particular architectural school and the terms its criteria rely on. That is an example of opinionated conceptual guidance, not evidence that every domain needs definitions. [Project glossary format](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/domain-modeling/CONTEXT-FORMAT.md), [codebase design](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/codebase-design/SKILL.md)

gstack provides a concrete coordination example: its simplification specialist emits one of five defined categories in a JSON finding contract. Downstream handling consumes that vocabulary. This demonstrates an implemented interface, without isolating a glossary's effect on quality. [Specialist contract](https://github.com/garrytan/gstack/blob/71f6048e8ada25180e61438abc1d98cb151fe9a7/review/specialists/simplification.md)

The research search found no controlled test of a short vocabulary section in Fable/Astra subagent domain guidance. A nearby multi-agent glossary study changes control flow at the same time and reports inconclusive results, so it cannot settle this question. [ACL study](https://aclanthology.org/2025.tsar-1.6.pdf)

For Orchflows, clarify **skill, workflow, guidance, primitive, library, and load versus launch** in their existing architectural owner if actual confusion remains. Do not duplicate those definitions across six domains. The current selection contract says makers and reviewers apply their respective sections: adding a common preamble would also require making its shared applicability explicit. A new heading alone does not ensure both agents use it.

**Audit of every shipped guidance file**

Word counts include headings. These files are already short: 1,129 words total, selected by domain rather than all universally applicable. My concern is how particular sentences influence work, not their raw length. The following judgments are editorial recommendations to test.

| File | Words | Preserve | Tighten or reconsider |
| --- | ---: | --- | --- |
| `code.md` | 217 | Observable behavior; deliberate compatibility changes; tests that detect the defect and survive refactoring; review findings with a trigger and consequence. | “Trace the relevant path” and “Treat dependencies, migrations and generated output as part of the change” are candidates for deletion or combination. Scope verification to actual consequences and give it a stopping condition. Ownership should be a criterion for a proposed change, not an invitation to refactor neighboring code. |
| `code.api.md` | 132 | Absent/empty/invalid distinctions; retry effects; bounded collections; recoverable errors; deliberate contract changes. | This is the most concentrated specialization. Keep the concrete distinctions. Make the review's request cases conditional on the interface; avoid reading the list as a mandatory suite for every API edit. A glossary is unnecessary unless the particular API redefines a term. |
| `research.md` | 193 | Claim-to-source traceability; independent rather than copied corroboration; time, population and uncertainty; missing evidence versus evidence of absence. | Combine overlapping provenance/corroboration sentences. Remove rhetorical summaries such as “A polished bibliography cannot compensate for weak support.” Keep counterevidence proportional to claims that could change the answer, without inventing a universal source count. |
| `writing.md` | 196 | Audience and intended decision; preserved meaning and qualifications; clarity over personal reviewer taste. | The largest proportion of generic composition teaching: paragraph jobs, voice/formality/rhythm, rereading the whole piece. Test a substantially shorter version. Put house style and genre preferences in extensions; avoid permanent bans on formatting, metaphor or particular words across all writing. |
| `visual-design.md` | 193 | Inspect the actual rendered artifact in its medium; legibility, hierarchy, accessibility and task completion; distinguish defects from aesthetic alternatives. | Retain rendered inspection explicitly in both Make and Review. Test trimming general advice about consistent typography, color and alignment. Keep interface and static-output conditions explicit; leave fashionable aesthetic preferences to specialized guidance. |
| `data-analysis.md` | 198 | Unit of observation, population, denominator, join cardinality, selection bias, traceable transformations and inference limits. | Keep these consequential checks; compress introductory teaching. “Recompute the central result or check it through an independent calculation” can become expensive when the result is a large model. Specify sufficient independent validation for the claim rather than implying every analysis must be rerun completely. |

A shorter Code candidate illustrates the intended direction; it is **not a tested replacement**:

> **Make:** Deliver the requested behavior while preserving unrelated contracts. Prefer a clear owner and a simple implementation. Verify the changed behavior and consequential failure modes; stop when required checks pass and no material concern remains.
>
> **Review:** Identify concrete defects and regressions with evidence, a trigger and a consequence. Judge tests by the behavior they can detect. Separate necessary fixes from stylistic alternatives and state what remains unverified.

This keeps preferences that affect decisions. It would still need comparison against the current guide, particularly for loss of useful compatibility and regression-testing detail. Applying the same compression percentage to every domain would be arbitrary.

**Structure and durability**

Make/Review is a good fit for this library because it aligns guidance with the responsibilities of the two primitives. None of the sources establishes it as an optimal universal format. I would keep it without adding required sections, scoring systems or an inheritance framework.

An entry belongs in persistent guidance when it changes a consequential choice: which tradeoff to prefer, what local meaning to use, or what evidence makes a result acceptable. Familiar professional advice can still be worth keeping if it reliably changes outcomes; apparent obviousness alone does not prove redundancy. Conversely, an elegant sentence with no measured effect is a deletion candidate.

Audit the complete instruction bundle: host instructions, caller request, repository docs and selected guidance. Duplicate or conflicting rules across those layers matter more than whether one file looks concise. Keep each guidance section understandable for its intended role; apparent repetition across Make and Review can be necessary when each role receives only its own instructions.

Durability should mean stable responsibilities and easy revision. Model upgrades can also introduce new weaknesses, so some useful advice may need to be added or reinstated. The goal should be the smallest useful set for supported models, not a promise that every surviving sentence will last forever.

**What should change in principles.md**

The test I would now apply is: **does this explain a design choice another well-designed library could reasonably make differently?**

| Current principle | Assessment |
| --- | --- |
| 1. Trust model judgment | General value. Keep the Orchflows-specific consequence: model-dependent prescription is removable guidance, separate from composition. |
| 2. Use the host | Distinctive architectural boundary. Keep. |
| 3. Compose small pieces | Keep the specific semantics of skill composition and loading without another agent. |
| 4. Give each concern one owner | The slogan is generic code advice. The prompt/guidance/skill/script ownership mapping is specific and worth keeping. |
| 5. Follow dependencies | Mostly workflow policy. Retain the reason for avoiding task-size routing in the workflow's design rationale. |
| 6. Keep review independent | Distinctive primitive contract. Keep; exact review counts remain with workflows. |
| 7. Simplest complete solution | General Code guidance. Remove from principles rather than repeat it in a new extension. |
| 8. Prove, then prune | General empirical method until tied to this library's ordinary-request trials and deletion of unnecessary prescription. Keep that specific meaning. |

I would therefore narrow the document around five decisions: **native execution; composition without extra coordinators; ownership by reason for change; independent judgment; and workflow usefulness demonstrated on ordinary requests.**

I would not turn all eight current principles into `code.orchflows`. An extension should contain additional coding criteria peculiar to this repository, such as keeping mechanism implementation out of workflow prose and avoiding a second runtime or log. It can reference the canonical architectural decisions. Repackaging the entire principles page would recreate the duplication you noticed.

**A bounded way to settle the remaining uncertainty**

Compare four conditions: no domain guidance, current guidance, a terse candidate, and that candidate plus only disputed/local vocabulary. Hold repository state, request, model, effort, harness, tools and delegation pattern fixed. The no-guidance condition must retain the same task facts and output contract; otherwise it tests missing information too.

Start with Code and Writing, where the deletion case is strongest, plus one task where multiple agents' outputs must fit together. Use repeated fresh runs, then expand to the other domains if the pilot is informative. Score finished quality, scope expansion, unsupported findings, integration repairs and terminology disagreements. Record time and tokens separately. Blind the scorer to the condition and use observable checks where available.

Check that the selected material actually reaches each worker. Compare improvements on held-out tasks before shipping. A small pilot will identify large failures and unnecessary instructions; it cannot prove tiny gains or permanent superiority. This testing method can use native transcripts and existing trials, without adding another Orchflows subsystem.
