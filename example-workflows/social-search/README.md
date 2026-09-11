# Social Search

A small library built from orchflows-light's two delegation primitives. Source profiles are partial applications of a generic site-search workflow; a separate evidence reviewer accepts their results or independently supplied research.

```text
social-search — current coordinator
  fan out selected profiles through search-site
    delegate-work → one worker per source
      collect → prepare-evidence
  gather all outcomes
  rank-evidence
    delegate-review → one ranked, cited assessment
```

Launch available source workers before waiting. Capacity limits use waves. For N selected sources there are N workers and one final reviewer, with no source reviews or review-to-acquisition loop.

## Components

| Skill | Responsibility |
| --- | --- |
| [social-search](skills/social-search/SKILL.md) | Select sources, fan out, gather, request one review |
| [search-site](skills/search-site/SKILL.md) | Delegate a named-site search; return evidence or a handle for deferred gathering |
| [prepare-evidence](skills/prepare-evidence/SKILL.md) | Shape an inspectable handoff in the current worker |
| [rank-evidence](skills/rank-evidence/SKILL.md) | Delegate independent assessment of supplied evidence |
| Six [source profiles](skills/social-search/references/source-workflows.md) | Only source-specific knowledge |

An ordinary prompt supplies the question and any dates, sources, bounds or output preferences. There is no default date window. Native public tools are the default. Optional `research-acquire:research-acquire` belongs to a separate library; it is needed only when its acquisition capabilities are chosen.

These ten skills compose without extra coordinating agents. Search-site also works alone; rank-evidence needs no search run. Reviewers inspect support without editing source evidence or making new source reads. Required gaps remain visible in partial assessments.

## Install and use

From an available orchflows-light package, run `scripts/orchflows.py setup --example social-search` with Python 3.11+. This seeds `~/.orchflows/libraries/social-search` when absent and preserves existing libraries. Register the complete package with the native host; disk placement alone does not register it. Refresh cached installations after edits.

Public identities are `social-search:<skill-name>`. From another project, load the installed native skill or locate it with `resolve social-search --skill <skill-name>`. Core dependencies and one shared home history run follow [library context](references/library-context.md). A missing home runtime does not prevent native research if the core skills are available.

The [trial request](trials/request.md) and [acceptance criteria](trials/expected-behavior.md) test composition, evidence and actual agent behavior. [Provenance](references/provenance.md) records the upstream origin. Trial specifications are not claims of successful execution.
