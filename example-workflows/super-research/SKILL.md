---
name: super-research
description: Answer one bounded, keyless research question with cited, dated, gap-declared evidence from public platforms.
disable-model-invocation: true
---

Require: one bounded `question` naming its live sources, its `window`
where it has one, a frozen `as_of` at or after the run's own reads, and a
hard per-step cap.

Open the frame, its goal the answered question:

    tickets.py frame-open <run> --goal-file <question-goal> --workflow super-research


**Acquisition — one call per named source, launched together.**

    tickets.py do <run> --pack orch-research-pack --parent <frame>
      --goal-file <source-goal> --bound "<= 40 tool calls"

Each goal names one source, the window, the `as_of` and the cap, and
directs the child to enter the `super-research` skill by name with its
launch prompt forwarded verbatim, at the `SKILL.md` path
`orchflows list --kind skill` resolves — carry that path, so no child
searches; a body that opens a frame is this workflow's same-named
adapter. That skill's Require, Preparation, Never and Return bind the
child; its Return fills the `artifact: evidence:` line. Time-bounding is
per operation — the skill's `WINDOW_REACH` table decides — so a windowed
call whose operation cannot bound time at its origin returns
`window_not_honored`; name it in the goal, so the child files a gap, not
a silence. Keep each returned `artifact: evidence:<store-id>` line
verbatim; the next call is handed it.

**Coverage loop, at most two rounds.**

    tickets.py judge <run> --pack orch-research-pack --parent <frame>
      --artifacts evidence:<id> [--artifacts ...] --goal-file <coverage-goal>

The coverage goal asks one thing: which sub-questions no record answers,
and which typed losses came back. Keep the `findings: <path>` line
verbatim. Round two exists only for the gaps judge named — one `do` per
gap, quoting the finding and the source that closes it, then one final
`judge` over the enlarged set; a gap still open is declared.

**Report, one call, the frame's last.**

    tickets.py do <run> --pack orch-content-pack --parent <frame>
      --goal-file <report-goal> --bound "<= 40 tool calls"

Its goal hands every `artifact:` and `findings:` line verbatim and asks
for one self-contained rendered dossier — one HTML file, no external
fetch, legible in light and dark — answering first, then each source's
evidence dated and cited from its `normalized_locator`, every typed loss,
contradiction and open sub-question, under the skill's five report rules.
Keep its `artifact: doc:` line verbatim.

Never: average contradicting sources, read a typed loss as an absence,
quote a community comment without its author and count, or close over the
acquisition children with neither a coverage judge nor an
`unjudged: <reason>` journal line.

Return: `tickets.py frame-close <run> <frame> --done <verifier>`, whose
done is the dossier verifier over that `doc:` identity — every
load-bearing claim cited and dated, every loss stated, every unanswered
sub-question declared.
