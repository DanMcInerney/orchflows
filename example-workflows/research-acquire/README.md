# Research Acquire

Collect public evidence through bounded discovery, semantic selection and depth reads, preserving receipts and resumable state. It runs in the current agent with **no child agents**; the caller interprets the evidence.

## Use

After [installation](#install):

```text
Use research-acquire:research-acquire to collect Hacker News evidence about
SQLite in production from the last 30 days. Discover up to 10 stories,
then select at most 2 discussions worth reading, with up to 20 records each.
Use one plan capped at 3 steps, 8 requests, 50 records, and 120 seconds of
active acquisition. Save inspected evidence, selection reasons, receipts,
and resume state in research/sqlite-hn. Report any coverage gaps.
```

Supply the question, sources, date window, bounds and output location. The agent chooses depth reads from retained candidate text and context. One plan shares request reservations, pacing and limits across discovery, depth and resume. Completed steps make no further requests; uncertain reads retain their budget reservation and gap.

Bounds are ceilings. Active-work limits do not guarantee total wall time; a completed packet establishes neither complete coverage nor an answer.

## Supported sources

Routes use public access without credentials. The [source operations reference](skills/research-acquire/references/selection-routes.md) defines exact syntax, depth operations and limits.

| Source | Operations |
| --- | --- |
| Reddit | Archive discovery, listings/search, selected submissions and sampled comments |
| Hacker News | Story/comment search, discussion trees and items |
| GitHub | Anonymous repository search/details, issues and releases |
| Crossref/arXiv | Metadata, available abstracts and selected original-page reads |
| Web | Known HTTPS documents and extracted prose; host tools own discovery |
| RSS/Atom | Supplied feeds, entries and selected articles |
| X via FxTwitter | Known post IDs and returned conversation material through a third party |
| YouTube | Channel feeds; separate optional caption reader for known videos |

Abstracts remain abstracts; captions are speech; sampled comments remain a sample. These routes exclude JavaScript rendering, X search, automatic feed discovery and guaranteed complete conversations.

## Saved evidence

| Artifact | Contents |
| --- | --- |
| `packet.json` | Records, relationships, step outcomes and losses |
| `summary.json` | Packet hash, counts, timings, limits and gaps |
| `candidates.json`, `selection.json` | Available choices and selection reasons |
| `checkpoint.json`, step artifacts | Identities, reserved budgets and saved results |

Keep the directory together. Resume uses unchanged plan/output paths; [acquisition](skills/research-acquire/references/acquisition.md) defines identity, corruption and uncertain-read handling. New scope needs a separate plan within remaining caller bounds. The [YouTube reader](skills/research-acquire/references/source-inspection.md) writes a separate receipt and, when retained, timing-bearing caption sidecar.

## Install

From an Orchflows checkout with Python 3.11+:

```sh
python scripts/orchflows.py setup --example research-acquire
```

Register the home and install `research-acquire` using core `docs/hosts.md`, then start a new session. Setup preserves user-owned copies; update that copy before refreshing an existing install. Manual invocations are `$research-acquire:research-acquire` in Codex and `/research-acquire:research-acquire` in Claude Code.

The backend needs **Python 3.9+ and standard library**. Optional captions need `yt-dlp` in the same interpreter:

```sh
python -m pip install yt-dlp
```

Setup installs no library runtime dependencies; child delegation is unnecessary.

## Inspect or extend

Start with the [skill](skills/research-acquire/SKILL.md), [acquisition](skills/research-acquire/references/acquisition.md) and [routes](skills/research-acquire/references/selection-routes.md). [Protocol](skills/research-acquire/references/protocol.md) owns direct APIs/manual manifests. Mechanics and offline checks live in the skill's `scripts/` and `tests/`.

From the skill directory, set `PYTHONPATH` to its absolute `scripts/` path:

```sh
python -m unittest discover -s tests -t .
python scripts/acquire_fixture.py --output <scratch>
```

The fixture exercises parsing, selected depth and resume without live access. These checks establish neither live availability nor research quality.

Backend from [orchflows recent-search](https://github.com/DanMcInerney/orchflows/tree/945546721732aa564a086ee9543803b38017e1c3/example-workflows/recent-search), under its [MIT license](LICENSE).
