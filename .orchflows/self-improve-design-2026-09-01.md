# The self-improve design — sliced evidence, need-bought mining

2026-09-01. Status: PROPOSED. Successor to the shipped
`example-workflows/self-improve` body (the lego-migration conversion of
the mine/qualify/deliver pipeline), designed from scratch on the two
newest substrates: the lego design (PR #153 — bricks, frames, prose)
and the routing design (PR #154 — need-bought machinery). Evidence
base: the sink's friction streams (7,559 lines across 2026-07..09),
`improvement/covered.jsonl`'s matcher/watermark shape, the routing
design's D3 ruling (the `unjudged:`-mining loop is self-improve's
job), and the recorded stall of the previous template
(run 20260824T070000Z: "01-deliver STALLED on the template's
sealed-batch wedge, 5 template defects").

## The idea in one paragraph

The shipped workflow pays a fixed pipeline on every cycle — a frame,
a mine child fed raw month-scale streams (7,283 lines in 2026-08), a
qualify judge re-deciding arithmetic the mine already did, a deliver
child, a landed judge — regardless of how much evidence the window
holds. This design makes the cycle need-bought. One deterministic
**harvest** command slices the sink by any window (time range,
sessions, runs, project, workflow), drops covered evidence by the
matchers `covered.jsonl` already carries, clusters, and computes the
improvement law §4's recurrence arithmetic — zero agents. An empty
digest ends the cycle in seconds with no ticket. A small digest is
mined inline by the driver (act lane). Only scale or wanted
independence buys a mine brick; only a qualifying proposal buys the
deliver brick; A2 at frame-close is the only judge, and it reads the
seam. The window stops being a prose obligation and becomes flags.

## What the two refactors teach, applied here

1. **Lego:** composition is prose over two bricks; every guarantee
   lives in the mechanical trunk. Clustering, covered-exclusion, and
   recurrence counting are guarantees — they belong in a script, not
   in a child's context. The old mine child spent its budget being a
   bad, expensive `grep`.
2. **Routing:** buy machinery on evidence, never prediction; the
   empty set is a real tier; deterministic verdicts cost zero agents.
   The qualify judge is this design's `419a3f44` tombstone: §4's
   recurrence test is arithmetic, so a judge re-checking it was a
   prediction-priced agent. What genuinely needs judgment — causal
   owner, contradiction-vs-current-text, exactness of the change —
   stays with the mine; what proves exactness is the delivery's
   `done`, not a forecast of it.
3. **Routing D3:** A2's teeth are this workflow. `unjudged:` reasons,
   land outcomes, and stall verdicts must therefore be *cheap to
   mine* — which today they are not (they live inside per-run ticket
   markdown). That is the log-side change below.

## Move 1 — the harvest door (deterministic, zero agents)

New `scripts/harvest.py`, the read sibling of `scripts/friction.py`:
stdlib-only, sink resolution through `state_root.py`, read-only over
the sink, writes exactly one digest file at `--out`.

```
python harvest.py --out <digest.json>
  [--since <ts|7d>] [--until <ts>] [--on <date>]...
  [--session <id>]... [--run <id>]... [--project <name>]
  [--workflow <name>] [--skill <orch-name>] [--host <host>]
```

Selectors compose (AND across kinds, OR within a repeated flag). Time
composes the same way: each `--on <date>` is one whole day and the
flag repeats, so "last Wednesday and last Monday, alone" is two flags
with nothing between them. No selector means "everything since the
newest covered watermark". What it does, in order:

1. **Slice** `friction/*.jsonl` and `events/*.jsonl` (Move 2) by the
   window, on the provenance fields entries already carry.
2. **Exclude covered:** apply every `covered.jsonl` entry's `matcher`
   regex list to entries at or before its `watermark`; dropped
   entries are counted, never shown. Today this is a prose
   never-rule on the mine child; here it is mechanical and testable.
3. **Cluster** by observed-text similarity: normalize (case, paths,
   hashes, numbers), 3-word shingles, greedy union at a fixed Jaccard
   threshold. Deterministic given stream order. A mechanical
   approximation of §4's "grouped by observed-text similarity" — the
   mine may merge clusters freely; a split must restate the
   arithmetic over the split members.
4. **Compute §4:** per cluster — count, distinct sessions, distinct
   runs/hosts where sessions are absent — and mark `recurrence_met`.
   Contradiction and environment-probe qualification stay the mine's
   judgment; the digest only screens.

**`--list-runs` is the resolver mode.** The script is deterministic;
the *driver* is the natural-language layer — the same division the
lego design makes everywhere (prose interprets, the trunk guarantees).
`harvest.py --list-runs [window flags]` prints one line per run in
the window: run id, workflow name and goal first-line (from the
frame-open event), open/close timestamps, friction and event counts.
Fuzzy windows resolve in prose against that listing: "this last
workflow" is the newest line; "the scraper one from a while back" is
the line whose goal mentions the scraper; "last Wednesday and Monday"
is two `--on` dates the driver computes from today. The driver then
calls harvest with exact selectors. No fuzzy matching ever enters the
script — and the listing only knows workflow names because Move 2's
frame-open event records them.

The digest carries a header (window, streams read, totals, covered
exclusions applied) and clusters ranked by weight, each with:
`cluster_key` (slug from shared shingles), counts, `recurrence_met`,
a `matcher_draft` (the shared shingles as regexes, for the covered
line the delivery will write), the member entries verbatim capped at
12 per cluster with the overflow counted. Everything a proposal and
its covered line need is pre-formed; the old mine invented these
shapes ad hoc every cycle.

## Move 2 — the event stream (the log-side change)

`<sink>/events/<yyyy-mm>.jsonl`: one line per terminal machine event,
appended by the trunk scripts that already own the transition, with
the same provenance head friction entries carry (sink_convention, ts,
project, run, ticket, host, session) and the same monthly sharding
and locked-append idiom (`tickets.py:_append_one_line`). v1 events:

- `frame-open` — workflow name (this is what makes `--workflow` a
  selector: one workflow's every run, across all time, is a slice),
  goal digest.
- `frame-close` — child count, judged or the `unjudged: <reason>`
  text verbatim, suite exit.
- `land` — status, `done` exit, attempts, elapsed seconds.
- `stalled` — the two-identical-rounds verdict.

Why a stream and not a walk: D3 promised that `unjudged:` reasons and
land outcomes accumulate and get mined, but they live in `## Report`
sections of per-run markdown — mining them means parsing ticket trees
per harvest, forever. One append per event makes every future harvest
O(slice), makes cost mining (elapsed, attempts, spawn counts — the
speed-review class of finding) possible at all, and gives "mine a
single workflow" a mechanical meaning. No backfill: the stream starts
at delivery; pre-stream run evidence stays walkable by hand if ever
wanted. `friction.py` itself changes nothing — its recent provenance
work is exactly what harvest selects on.

Law placement: the stream is a sink channel — one sentence in
`rules/visibility.md` §6 beside `run-state`/`improvement`; writers
are `tickets_frame.py` and `tickets_land.py`. Untrusted-data law
unchanged: only installed scripts write it.

## Move 3 — the workflow, drafted verbatim

Replaces `example-workflows/self-improve/SKILL.md` (workflow tier,
450-word budget; this draft ~400):

> ---
> name: self-improve
> description: Harvest the sink's friction and event streams for a
>   chosen window, mine what qualifies into ranked proposals, and land
>   the top one in its causal owner. Use on demand or closing a run.
> disable-model-invocation: true
> ---
>
> Require a window — the harvest's flags — and, when delivering, a
> `workspace`: the repository holding the proposal's causal owner.
>
> **Harvest**, deterministic, zero agents:
>
>     python harvest.py --out <digest> [--since <ts|7d>] [--until <ts>]
>       [--on <date>]... [--session <id>]... [--run <id>]...
>       [--project <name>] [--workflow <name>] [--skill <orch-name>]
>
> A fuzzy window — "this last workflow", "the scraper run", "last
> Wednesday and Monday" — resolves first: `harvest.py --list-runs`
> prints the candidate runs (id, workflow, goal, counts); pick, then
> pass exact flags. One command slices friction and events by the
> window, drops what a covered matcher already answers, clusters, and
> marks each cluster meeting
> [the improvement law](../../rules/improvement.md) §4's recurrence
> arithmetic. The digest is the only evidence later steps
> read; raw streams are never handed to a child. An empty digest ends
> the cycle here — say so and stop: no frame, no ticket.
>
> **Mine.** A digest at or under 40 entries you mine yourself — the
> act lane: assign each qualifying cluster one causal owner, check any
> claimed contradiction against the owner's current text, and write
> ranked proposals through `tickets.py improvement --proposal`,
> carrying the digest's cluster_key, matcher and watermark verbatim;
> the proposal files are the record. Larger, or when independent eyes
> are wanted, spend one brick — the frame opens with the first brick:
>
>     tickets.py do <run> --pack orch-content-pack --parent <frame>
>       --goal-file <mine-goal> --bound "<= 40 tool calls"
>
> Its goal: the digest path, the same owner/contradiction/proposal
> obligations, and §4 as the ranking law. Either way the result names
> the top proposal — or the finding that nothing qualified, which
> closes the cycle.
>
> **Deliver**, unless invoked mine-only — one brick in `workspace`:
>
>     tickets.py do <run> --pack orch-code-pack --parent <frame>
>       --isolation required --goal-file <deliver-goal>
>       --bound "<= 120 tool calls"
>
> Its goal: the top proposal's exact change at its causal owner, its
> dependents holding, replay per §5 where the cluster holds a
> replayable item, `done` the owner's required gate at the landed
> revision — and, the last act, `tickets.py improvement --covered`
> with the digest-supplied line citing that revision.
>
> Frame law: re-read `## Report` before each decision, append through
> `result`, relay `artifact:` and `findings:` lines verbatim. Close
> with `frame-close`. With two or more do-children the judge reads the
> seam: the delivered change equals the top proposal, nothing edited
> outside its scope, the covered line present with a sane watermark. A
> single-child cycle closes `unjudged: single child; the owner's gate
> and the human-reviewed merge are the review`.
>
> Never: land a proposal the mine did not rank first, deliver more
> than one proposal per cycle, edit a friction entry, an event, or a
> prior covered line, rank on evidence the harvest excluded, or mark
> a criterion complete on the delivering child's own claim.

## Placement — where it lives, and how hosts pick it up

The canonical source is `example-workflows/self-improve/` and nothing
else. That is the lib ring: `install.py` puts the gallery under
`~/.orchflows/lib/`, `orchflows sync` renders the host adapters, and
both Claude Code and Codex resolve `/self-improve` from there. The
half-remembered "~/.orchflows so hosts pick it up" is satisfied by
the install, not by a second authored copy: a hand copy at
`~/.orchflows/workflows/self-improve/` would shadow the lib entry
(nearest-ring rule) and go stale on every upgrade. Users who *want* a
divergent variant copy the bundle out into their home ring on
purpose — the rings doc already blesses exactly that.

## Cost, before and after

| window | shipped workflow | this design |
| --- | --- | --- |
| quiet week, nothing new | frame + mine child over raw streams + judge | one harvest run, empty digest, stop — zero agents |
| one run / one workflow | same fixed pipeline | harvest `--run`/`--workflow`, inline mine — zero to one agent |
| month-scale mine + land | frame + 3–4 children, mine reads ~7.3k raw lines | frame + 2 children + seam judge; children read a digest |

The qualify judge is deleted everywhere. The mine child's bound drops
60 → 40 calls because slicing, exclusion, and counting left its job.

## What this deletes

- The qualify `judge` step (recurrence is harvest arithmetic; the
  delivery's `done` proves exactness; §2's human-reviewed merge was
  always the real activation gate).
- The landed-artifact judge as a standing step (A2's seam judge at
  close covers the two-child cycle; single-child cycles say why).
- The mandatory frame (opens with the first brick, never before).
- Raw-stream reading by any child, and with it the covered-exclusion
  and window-selection prose obligations (now mechanical).

## Eyes-open costs

1. Mechanical clustering is an approximation; a bad threshold splits
   a real cluster below the bar. Mitigation: the mine may merge
   freely, and the threshold is one constant with a fixture corpus.
2. The event stream starts empty — `--workflow` selection and cost
   mining only accrue value going forward. Accepted; no backfill.
3. Inline mining lets the driver mine its own session's friction —
   less independence than a child. Bounded: 40 entries, proposals
   are passive (§2), and the deliver brick plus seam judge stay
   independent. The digest cap is the tripwire, in the body.
4. `harvest.py` is new trunk surface: needs its own tests (window
   edges, matcher exclusion, cluster determinism, Windows paths).

## Delivery scope

- M1: `scripts/harvest.py` + tests + installer/receipt entry.
- M2: event emission in `tickets_frame.py`/`tickets_land.py` + the
  visibility §6 sentence + tests (one event per transition, locked
  append, provenance head).
- M3: the SKILL.md body above into `example-workflows/self-improve/`;
  validator word-count green; scratch-run admission per the authoring
  doc §Procedure 4.
- M4: `rules/improvement.md` §6's cycle sentence re-pointed at the
  new shape (mine→deliver wording survives; the qualify step goes);
  §4 unchanged — harvest implements it, it does not own it.
- M5: mark the old body's goal-file templates superseded where they
  live; friction entries about the sealed-batch wedge become the
  first covered candidates of the new cycle.

## Acceptance at the tip

Gate + preflight green. Harvest over `--since 2026-08-01 --until
2026-09-01` reproduces the known August clusters and drops every
covered-matcher hit; `--run 20260901T021739Z` yields only that run's
entries; an empty window prints the empty verdict and the workflow
stops with zero tickets in the sink. A full cycle on a real qualifying
cluster lands one change, appends one covered line, and closes its
frame with a seam judge — two do-children, one judge, no qualify
child anywhere in the tree.
