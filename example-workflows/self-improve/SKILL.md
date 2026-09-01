---
name: self-improve
description: Harvest the sink's friction and events, mine what qualifies, and land the top proposal at its causal owner. Use on demand or closing a run.
disable-model-invocation: true
---

Require: a window — the harvest's flags — and, when delivering, a
`workspace`: the repository holding the proposal's causal owner.

**Harvest**, deterministic, zero agents:

    python harvest.py --out <digest> [--since <ts|7d>] [--until <ts>]
      [--on <date>]... [--session <id>]... [--run <id>]...
      [--project <name>] [--workflow <name>] [--skill <orch-name>]

A fuzzy window — "this last workflow" — resolves first:
`harvest.py --list-runs` prints candidate runs (id, workflow, goal,
counts); pass exact flags. One command slices friction and events
by the window, drops what a covered matcher already answers,
clusters, and marks each cluster meeting
[the improvement law](../../rules/improvement.md) §4's recurrence
arithmetic. The digest is the only evidence later steps read; raw
streams never reach a child. An empty digest ends the cycle here —
say so and stop: no frame, no ticket.

**Mine.** A digest at or under 40 entries you mine yourself — the
direct lane: assign each qualifying cluster one causal owner, check any
claimed contradiction against the owner's current text, and write
ranked proposals through `tickets.py improvement --proposal`,
carrying the digest's cluster_key, matcher_draft and watermark
verbatim. Larger, or when independent eyes are wanted, spend one
callable:

    tickets.py do <run> --pack orch-content-pack --parent <frame>
      --goal-file <mine-goal> --bound "<= 40 tool calls"

Its goal: the digest path, the same owner/contradiction/proposal
obligations, and §4 as the ranking law. Either way the result names
the top proposal — or the finding that nothing qualified, which
closes the cycle.

**Deliver**, unless invoked mine-only — one callable in `workspace`:

    tickets.py do <run> --pack orch-code-pack --parent <frame>
      --isolation required --goal-file <deliver-goal>
      --bound "<= 120 tool calls"

Its goal: the top proposal's exact change at its causal owner, its
dependents holding, replay per §5 where the cluster holds a
replayable item, `done` the owner's required gate at the landed
revision — and, the last act, `tickets.py improvement --covered`
with the digest-supplied line citing that revision.

Frame law: the first callable, mine's or deliver's, opens it.

    tickets.py frame-open <run> --goal-file <frame-goal> --workflow self-improve

Reread `## Report` before deciding, log each `result`; keep
`artifact:` or `findings:` word for word. Close with `frame-close`.
With two or more do-children the judge reads the seam: the delivered
change equals the top proposal, nothing edited outside its scope,
the covered line present with a sane watermark. A single-child cycle
closes `unjudged: single child; the owner's gate and the
human-reviewed merge are the review`.

Never: land a proposal the mine did not rank first, deliver more
than one proposal per cycle, edit a friction entry, an event, or a
prior covered line, rank on evidence the harvest excluded, or mark
a criterion complete on the delivering child's own claim.

Return: `tickets.py frame-close <run> <frame> --done <gate>`, the
owner's required gate at the landed revision, read outside the
delivery.
