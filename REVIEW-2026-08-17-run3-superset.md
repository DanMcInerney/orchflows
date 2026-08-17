# Run 3: the same question, after the roadmap

Part 4, and the close of the bakeoff. Entry point:
[REVIEW-2026-08-17-super-research-bakeoff.md](REVIEW-2026-08-17-super-research-bakeoff.md).

Same question, same window, same host, same day. What changed is the package.

## 1. The comparison

| | run 1 `last30days` | run 2 `super-research` (before) | run 3 `super-research` (after) |
|---|---|---|---|
| wall clock | 92.4 s | ~45 min | **2.2 s** |
| cost | 1 context | 8 agents, ~1.4M tokens | **1 context, 0 subagents** |
| records | 58 | ~198 | 172 |
| **records carrying engagement** | most | **4** | **81** |
| platforms answering | 4 | 6 | **8** |
| Reddit comments | 3,462 counted, none read | 0 | **46 read, scored** |
| video content | 2 transcripts | 0 (titles only) | **1 transcript, 19,329 chars** |
| prediction markets | 0 after filtering | route did not exist | **27 markets, a full SPCX price ladder** |
| X | 0 (unauthenticated) | 36 posts, 0 on-topic | **20 posts, on-topic** |
| provenance | none | full | full |
| relevance floor | invisible, 376 dropped | none | **auditable: 20 kept, 152 dropped, each listed** |

Run 2's diagnosis was *"discovers competitively and hydrates almost nothing"*.
Engagement-bearing records went from 4 to 81 on the same question.

## 2. What the run now reaches

One `fused` manifest, ten steps, ten lanes overlapping — an origin still sees one
read at a time, because the governor locks per host and paces per route.

```
rd-search    partial  kept=7    reddit_shreddit  search, sorted top, windowed
rd-stocks    partial  kept=7    reddit_shreddit  r/stocks search
rd-comments  ok       kept=25   reddit_shreddit  one thread's comments, scored
hn           partial  kept=25   hacker_news      windowed server-side, typo-tolerance off
news         ok       kept=11   web_search       Bing news RSS
gnews        partial  kept=15   web_search       Google News RSS, when:30d
st           ok       kept=30   stocktwits       SPCX stream with Bullish/Bearish labels
mkt          partial  kept=30   prediction_markets  Polymarket
x            partial  kept=20   x_fxtwitter      the one keyless X search
yt           ok       kept=2    youtube_innertube   player + transcript
```

The evidence the review named as decisive and unreachable, now present:

- **Polymarket's SPCX price ladder** — "Will SpaceX (SPCX) hit $145 / $140 / …
  $105 in August?" — which is the "up or down" question asked literally, with
  money on it. Review D-7: *"For a literal 'up or down' question, market odds are
  the highest-signal evidence available, and the roster has no such adapter."*
- **Reddit comments with scores**, from the platform's own client surface. Review
  D-1: *"No Reddit comment route exists at all, so comment-level sentiment — the
  densest surface for this question — is unreachable."*
- **The bull/bear thesis as words**: 537 cues, 19,329 characters, opening *"SpaceX
  is falling, following their second quarter 2026 earnings update… has lost
  roughly 50% of its value."* Review D-5: *"A 20-minute bull thesis is a title."*
- **An X post on topic**: "Early, but not wrong. $SPCX short squeeze loading."
  Review D-2: *"36 records, 0 on-topic; lane can only measure publisher voice."*

## 3. What did not change, on purpose

The spine the review said to keep. Typed loss is still the finding; the access
ladder still labels every record and no capability depends on `K5`; discovery is
still never merged into hydration; the replay is still frozen; nothing retries,
falls back, or answers a 429 with a changed identity; and the package still
refuses to rank, judge or synthesize — the ordering above is
`relevance.partition`, which hands back the 152 records it dropped along with the
20 it kept, so the floor is a decision with a record rather than an invisible one.

Two refusals worth naming, because they cost recall and were taken anyway:
**PullPush** asked in a 429 body not to be scraped by agents, so no route is
declared for it; and Reddit's **`more-comments`** continuation wants a POST, which
this package admits on two named routes and nowhere else, so a comment page states
the cap it hit rather than reaching past it.

## 4. The measurement that mattered most

Not a route — a parameter. Hacker News's index reached `space` from `SpaceX` and
answered **849,432** hits where the exact query answers **67,207**; the top rows
of the loose answer were about Go release notes and "Apple's space". Every search
this package makes now sends `typoTolerance=false`. That is review D-22 —
*"a token match is not a topic match"* — and its cause turned out to be one
default nobody had looked at.
