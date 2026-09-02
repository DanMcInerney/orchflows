---
name: super-research
description: Answer one bounded, keyless research question with cited, dated, gap-declared evidence from public platforms.
disable-model-invocation: true
---

Require: one bounded `question` naming the live sources it reaches, the
`window` it is asked over where it has one, a frozen `as_of` at or after
this run's own reads, and a hard per-step item cap.

Open the frame first, its goal the answered question:

    tickets.py frame-open <run> --goal-file <question-goal> --workflow super-research

The frame's `## Report` is your working memory, not a courtesy. Begin every
wave by re-reading the frame and its children from the sink, then append
that wave's decision with `tickets.py result <run> <frame> --by <frame>`.

**Acquisition — one call per named source, all launched together.** For
each source the question names, one line:

    tickets.py do <run> --pack orch-research-pack --parent <frame>
      --goal-file <source-goal> --bound "<= 40 tool calls"

Each source goal names exactly one source, the window, the frozen `as_of`
and the cap, and directs the child to enter the `super-research` skill by
name, forwarding its own launch prompt verbatim, at the `SKILL.md` path
`orchflows list --kind skill` resolves — the goal carries that path, so no
child searches for it, and a body that opens a frame is this workflow's
adapter sharing the name, never the skill. That skill's own Require,
Preparation, Never and Return bind the child and are not restated here; its
Return is what fills the `artifact: evidence:` line. Time-bounding is
declared per operation, not per source — that skill's own `WINDOW_REACH`
table is the authority — so a windowed call whose operation cannot bound
time at its origin comes back carrying `window_not_honored`.
Name that in the goal, so the child files a declared gap rather than a
silence. Keep each returned `artifact: evidence:<store-id>` line verbatim;
it is what the next call is handed.

**Coverage loop, at most two rounds.**

    tickets.py judge <run> --pack orch-research-pack --parent <frame>
      --artifacts evidence:<id> [--artifacts ...] --goal-file <coverage-goal>

The coverage goal asks one thing: which sub-questions no record answers,
and which typed losses the acquisition returned. Keep the returned
`findings: <path>` line verbatim. Round two exists only for the gaps that
judge named — one further `do` per named gap, quoting the finding and the
source that can close it, then one final `judge` over the enlarged set.
Two rounds is the bound; a gap still open is declared in the answer.

Never: average contradicting sources, read a typed loss as an absence,
quote a community comment without its author and count, or close over the
acquisition children with neither a coverage judge nor an
`unjudged: <reason>` journal line.

Return: `tickets.py frame-close <run> <frame> --done <verifier>`, whose
done is the dossier verifier — every load-bearing claim cited from its
`normalized_locator` and dated, every loss stated, every unanswered
sub-question declared.
