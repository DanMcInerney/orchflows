# Research Acquire

**Every research rabbit hole needs a budget and a way back.**

Research Acquire gives your agent a bounded way to collect public evidence: discover candidates, choose the ones worth reading, fetch their details, and save the evidence with receipts. An interrupted run can resume from its checkpoint with the same plan and remaining budget.

It works inside the current agent. **Zero child agents.** The caller decides what the evidence means.

## Try it

After [installation](#install), paste this into your agent:

```text
Use research-acquire:research-acquire to collect Hacker News evidence about
SQLite in production from the last 30 days. Discover up to 10 stories,
then select at most 2 discussions worth reading, with up to 20 records each.
Use one plan capped at 3 steps, 8 requests, 50 records, and 120 seconds of
active acquisition. Save inspected evidence, selection reasons, receipts,
and resume state in research/sqlite-hn. Report any coverage gaps.
```

Use it inside a larger research workflow, to deepen known leads, or to collect a reproducible evidence packet for later assessment. Supply the question, sources, date window, bounds, and output location.

## Follow the evidence, keep the receipts

```text
Discovery → candidate list → agent selects with reasons → depth reads
                                                           ↓
                                             Evidence + receipts + checkpoint
```

- **Spend reads where they matter.** The agent selects candidates from their retained text and context before fetching deeper material.
- **Carry the budget through resume.** One plan shares request reservations, source pacing, and limits across discovery and depth. Completed steps make no more requests when resumed.
- **Preserve what happened.** Evidence records, selection reasons, source outcomes, losses, and budget usage remain inspectable.
- **Keep uncertainty visible.** If a read started but its result was never saved, resume retains the uncertain gap. Source refusals and partial coverage stay in the handoff.

Bounds are ceilings. Active-work limits do not guarantee total wall time, and a completed packet does not establish complete source coverage or answer the research question.

## What it can read

The included routes use public access without credentials. Availability depends on the source; the [source operations reference](skills/research-acquire/references/selection-routes.md) defines exact queries, depth operations, and limits.

| Source | Included operations |
| --- | --- |
| Reddit | Archive discovery, public listings/search, selected submissions and sampled comments |
| Hacker News | Story/comment search and selected discussion trees or items |
| GitHub | Anonymous repository search, repository details, issues, and releases |
| Crossref and arXiv | Paper metadata and available abstracts; selected original-page reads |
| Public web pages | Known HTTPS documents and available extracted prose; discovery uses host tools |
| RSS and Atom | Supplied feed URLs, entries, and selected article reads |
| X via FxTwitter | Known post IDs and returned conversation material through a third-party provider |
| YouTube | Channel feeds; a separate optional reader for a known video's captions |

An abstract remains an abstract. Captions are video speech. Sampled comments remain a sample. JavaScript rendering, X search, automatic feed discovery, and complete conversation coverage are outside these routes.

## What lands in your workspace

| Artifact | Why you want it |
| --- | --- |
| `packet.json` | Evidence records, relationships, step outcomes, and losses |
| `summary.json` | Packet hash, counts, timings, limits, and gaps |
| `candidates.json` and `selection.json` | What the agent could choose and why it chose |
| `checkpoint.json` and step artifacts | Identities, reserved budgets, and saved results needed to resume |

Keep the output directory together. Resume uses the unchanged plan and output location; identity changes, corruption, and uncertain reads have explicit handling in the [acquisition method](skills/research-acquire/references/acquisition.md). New scope needs a separate plan within the caller's remaining bounds.

The optional [YouTube reader](skills/research-acquire/references/source-inspection.md) writes a separate caption receipt and, when retained, a timing-bearing caption sidecar.

## Install

From a complete Orchflows checkout with Python 3.11+:

```sh
python scripts/orchflows.py setup --example research-acquire
```

Register the home and install `research-acquire` for your host using core's `docs/hosts.md`, then start a new session. Setup preserves existing user-owned library copies; apply example updates to that copy before refreshing an existing install.

The skill is manual-only by default: `$research-acquire:research-acquire` in Codex or `/research-acquire:research-acquire` in Claude Code.

The acquisition backend requires **Python 3.9+ and the standard library**. The optional YouTube reader needs `yt-dlp` in the same interpreter:

```sh
python -m pip install yt-dlp
```

Setup installs no library runtime dependencies. This skill runs in the current context and requires no child delegation.

## Inspect or extend it

Start with the [skill](skills/research-acquire/SKILL.md), [acquisition method](skills/research-acquire/references/acquisition.md), and [supported routes](skills/research-acquire/references/selection-routes.md). The [protocol](skills/research-acquire/references/protocol.md) covers direct APIs and manual manifests. Mechanics live in `skills/research-acquire/scripts/`; offline checks live beside them in `tests/`.

From the skill directory, with `PYTHONPATH` set to its absolute `scripts/` path:

```sh
python -m unittest discover -s tests -t .
python scripts/acquire_fixture.py --output <scratch>
```

The fixture exercises parsing, selected depth, and resume offline. Neither it nor the unit suite establishes live access or research quality.

Backend from [orchflows recent-search](https://github.com/DanMcInerney/orchflows/tree/945546721732aa564a086ee9543803b38017e1c3/example-workflows/recent-search), under its [MIT license](LICENSE).
