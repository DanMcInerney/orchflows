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

**Acquisition** — *fan-out*: "One `do` per named item, launched together
under the frame; the shape line lists them as one wave."

    tickets.py do <run> --pack orch-research-pack --skill research-acquire
      --parent <frame> --goal-file <source-goal> --bound "<= 40 tool calls"

Each goal names one source, the window, the `as_of` and the cap. Time-bounding
is per operation — `research-acquire`'s `WINDOW_REACH` table decides — so a
windowed call whose operation cannot bound time at its origin returns
`window_not_honored`; name that source in the goal, so the child files a gap
rather than a silence.

**Coverage loop, at most two rounds.**

    tickets.py judge <run> --pack orch-research-pack --parent <frame>
      --artifacts evidence:<id> [--artifacts ...] --goal-file <coverage-goal>

The coverage goal asks one thing: which sub-questions no record answers,
and which typed losses came back. Round two exists only for the gaps that
judge named — one `do` per gap, quoting the finding and the source that
closes it, then one final `judge` over the enlarged set — and a gap still
open is *declare-gaps*: "A
gap that remains is written as a gap, `[]` when there is none; silence is a
defect."

**Report, one call, the frame's last.**

    tickets.py do <run> --pack orch-content-pack --parent <frame>
      --sheet html-dossier --goal-file <report-goal> --bound "<= 40 tool calls"

Its goal asks for one dossier answering the question first, then each
source's evidence dated and cited from its `normalized_locator`, every typed
loss, contradiction and open sub-question, and each market's own price
string with the markets that already resolved dropped.

Never: average contradicting sources, read a typed loss as an absence, or
quote a community comment without its author and count.

Return: `tickets.py frame-close <run> <frame> --done <verifier>`, whose
done is the dossier verifier over that `doc:` identity — every
load-bearing claim cited and dated, every loss stated, every unanswered
sub-question declared.
