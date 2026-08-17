# Bakeoff run 2: `super-research` composition on SpaceX stock sentiment

Part 2 of 3. Entry point and analysis: [REVIEW-2026-08-17-super-research-bakeoff.md](REVIEW-2026-08-17-super-research-bakeoff.md).
Run 1: [REVIEW-2026-08-17-bakeoff-run1-last30days.md](REVIEW-2026-08-17-bakeoff-run1-last30days.md).

- Date: 2026-08-17
- Question: identical to run 1, focused on the last 30 days
- Item: `.orchflows/skills/super-research` (worktree copy), 14 adapters / 18 route surfaces
- Frozen `as_of`: `2026-08-17T12:00:00Z`; window 2026-07-18 to 2026-08-17
- Composition: 1 `orch-planner` (Opus 5) + 6 `orch-worker` lanes (Opus 5) + direct main-lane re-dispatch
- Total subagent cost: **~1,404,000 tokens** across 8 agents; ~45 min wall clock

Per `SKILL.md`, super-research acquires only. It must never plan, rank, judge or synthesize -
those belong to the calling lane. Every worker was instructed accordingly and all six complied.

## 1. Route liveness, measured before dispatch

One bounded `cli smoke --adapter <id>` each, 2026-08-17T12:11-12:13Z:

| adapter | class | exit | state | typed loss |
|---|---|---|---|---|
| `hacker_news` | K0 | 0 | verified | - |
| `reddit_archive` | K3 | 0 | verified | `third_party_archive` standing |
| `reddit_feed` | K0 | 0 | verified | `engagement_unavailable` standing |
| `public_page` | K0 | 0 | verified | - |
| `web_search` | K4 | 1 | unverified | `http_status` - **HTTP 202 from ddg_html** |
| `x_syndication` | K2 | 1 | unverified | `rate_limited` - **HTTP 429** |
| `youtube_innertube` | K1 | 1 | unverified | `attestation_required` - 200 + playability `UNPLAYABLE` |

Not smoked: `x_guest`, `github_rest`, `rss_atom`, `linkedin_jobs`, `linkedin_public`,
`instagram_public`, `fake`.

Exit 1 means the origin answered and the roster row was not carried; exit 3 would mean nothing
answered. All three failures were exit 1, i.e. route-level, not network.

## 2. Planner output (Opus 5, 195,749 tokens on its first turn)

Produced 14 manifests across 6 lanes, all validated against `schema.parse_manifest` before dispatch,
planned ceiling 240 items. It also derived six operating rules from the package source that shaped
every lane, of which three were load-bearing:

- **R1 - a multi-hit hydration step can starve its own later hits.** `runner.run_step` tests
  `len(records) >= step.max_items` at the top of each call and breaks. So a hydration step with 3
  hits and `max_items 12`, where call 1 returns 100 records, keeps 12, marks
  `recall_window_partial`, and **never calls hits 2 and 3.** Hence one hit per step for
  `x_syndication` (~100 entries/call) and `youtube_innertube` `next:` (~20 comments/call).
- **R2 - lineage edges only form from `web_search`.** `normalize.link_discovery_hydration` builds an
  edge only from a record whose `representation_kind == "index"`, and `web_search` is the only
  adapter emitting `index`. `reddit_feed` is `feed`; HN Algolia and YouTube search are `native`. A
  *fused* manifest holding one of those discoveries plus its own hydration produces no edge, and
  `normalize.type_discovery_gaps` then stamps **`discovery_not_recorded` on every hydration record**
  - a false alarm about the run's own work. Hence every discovery->hydration pair was staged as two
  manifests, with manifest 2 hydration-only.
- **R5 - a snippet is prose, not a field.** A `web_search` `body` reading "412 upvotes" is text about
  a target this run did not hydrate; never liftable into an engagement value. Likewise
  `youtube_innertube` `viewCountText` / `publishedTimeText` are rounded locale strings.

Its own recall grading, pre-run: HN good; Reddit **structurally bounded**; X **structurally bounded
plus degraded**; open web degraded on discovery and structurally bounded on hydration; YouTube
degraded pending its own test.

## 3. Lane results

### L1 - Reddit community freshness (`reddit_feed` -> `reddit_archive`)

| step | outcome | loss | recv | kept |
|---|---|---|---|---|
| rf-stocks | partial | `recall_window_partial` | 25 | 8 |
| rf-investing | partial | `recall_window_partial` | 25 | 8 |
| rf-wallstreetbets | **failed** | `rate_limited` (429) | 0 | 0 |
| rf-stockmarket | **failed** | `rate_limited` (429) | 0 | 0 |
| rf-spacexlounge | partial | `recall_window_partial` | 25 | 8 |

24 records, all K0 / `authoritative` / `engagement=()` with `engagement_unavailable`, and
`community=""` (this route does not declare the subreddit - it exists only in the locator path).

**Step B made zero calls.** `SPCX` appears in zero titles. The one title containing "SpaceX" was an
r/SpaceXLounge Musk-scope sticky carrying no equity term. Arctic Shift was never asked, so there is
no `empty` to misread. Confirmed by parse alone: a hydration step with `selected_hits=[]` raises
`ManifestError: step ra-hydrate is a hydration step and requires selected_hits`.

Main-lane re-dispatch at `max_items: 25` (the planner's own confirmed cap defect - see run 3 D-12):
r/wallstreetbets and r/StockMarket both `ok`, 25/25 each, **no `recall_window_partial`**, 50 records.
Across r/wallstreetbets' newest 25 the strings `spcx`, `spacex`, `starship`, `starlink`, `starbase`,
`musk` **do not appear at all**. Titles were AMD/MU/KLAR/MSTR/Citigroup/Anthropic-IPO/crude, all
dated 2026-08-17. **The feed reaches roughly 1-3 days, not 30.**

One on-topic title surfaced in r/StockMarket and was hydrated:

```
title            : Nvidia discloses $21 billion stake in SpaceX at end of second quarter
author           : Force_Hammer
community        : StockMarket
canonical_locator: https://www.reddit.com/r/StockMarket/comments/1voqvuz/nvidia_discloses_21_billion_stake_in_spacex_at/
published_at     : 2026-08-15T02:33:27Z   time_confidence: reported
access_class     : K3   route_id: arctic_shift_posts_ids   operator: arctic-shift
engagement       : score=874, num_comments=89  (observed 2026-08-17T12:34:39Z)
record loss      : ['third_party_archive']
```

**This is the only Reddit engagement number the entire composition produced, and run 1 missed the
item entirely.** Note `time_confidence: reported`, not `authoritative` - an archive reported Reddit's
numbers rather than Reddit stating them. `edges=0`, correctly, because this was a hydration-only
dispatch, and `discovery_not_recorded` correctly stayed silent.

### L2 - Hacker News (`hn_algolia_search` -> `hn_firebase_item`)

7 discovery steps (the planner's 3 plus 4 listed substitutions, which the worker ran as additions and
the planner ratified) and 1 hydration step, later extended by 2 authorized item calls.

- 6 discovery steps: `partial` / `recall_window_partial` (20 received, 10 kept - Algolia page vs cap)
- `comments:SPCX short squeeze`: **outcome `ok`, loss none, exactly 2 rows** - the index had 2 matches,
  not zero. Distinct from `empty` (never got one) and `schema_drift` (never raised)
- Step B hydration: `ok`, no loss, 4/4; plus L2d: `ok`, no loss, 2/2
- Never observed anywhere: `field_omitted`, `http_status`, `malformed_json`, `schema_drift`,
  `rate_limited`, `unreachable`
- **K0 and `authoritative` on 68/68 records; `third_party_archive` appears nowhere.** Confirmed from
  records, not assumed

68 records total, **47 in-window**. But the corpus of record is far smaller:

- Of 62 discovery records, 29 contain a SPCX/SpaceX token; **13 of those are in-window**
- 3 of 4 hydrated stories are in-window
- **In-window on-topic corpus: 17 records - and 14 of them carry no engagement signal at all**
- The 9 in-window "stories" are **6 unique items**: 3 SpaceX stories each appear twice, once per
  `representation_kind`. Deduping by `native_item_id` would silently collapse two representations
- The 4 SpaceX stories total **16 points and 1 comment** between them

Two findings that bound any use of this lane:

- **`search_by_date:SPCX` token-matched loosely** - it matched the *authors* `SPCECDET` and `spixy`,
  and **27 of 56 comment bodies never contain the token**. Row count on a ticker query is not a
  measure of topic volume.
- **Algolia publishes no engagement for comments at all.** The argument on HN lives in comments, so no
  engagement-weighted read of the comment corpus is possible from this lane.

The two extra hydrations produced the lane's most valuable and most cautionary records:

- **`49061408` (groby_b)** - in-window, quantitative: **"almost 50% of the float is loaned out"**,
  naming the earnings call as catalyst. It contains **no SpaceX token**, so every lexical cut classed
  it "silent" while it is squarely on-question, and **it never appeared in the discovery set at all.**
  Both runs' retrieval missed this datapoint.
- **`49189113`** - 138 points, **282 descendants**, 57 kids - is a story about an X product exec
  stepping down, with no SpaceX token and no market term. A lockup remark sits inside it as an
  incidental aside. Weighting that comment by its parent thread would attribute 282 comments of
  unrelated argument to SPCX sentiment. Standing rule adopted: **never weight a comment by its parent
  thread's engagement.**

The worker also self-caught two false positives it had introduced by implementing the planner's
market-term list as a bare alternation: `valuation` matching inside "e-**valuation**" (a USB-C cable
impedance thread) and `shares?` matching "**share**" the verb (a LoRa mesh thread). True in-window
market-term count was **one**, not three.

### L3 - Open-web index sweep (`ddg_html` -> `public_page_article`)

| step | query | outcome | loss | kept | warning |
|---|---|---|---|---|---|
| ws-targets | `SPCX stock price target analyst bull bear` | failed | `http_status` | 0 | `http status 202 from ddg_html` |
| ws-lockup | `SPCX lockup expiration short interest squeeze` | failed | `http_status` | 0 | same |
| ws-fundamentals | `SpaceX earnings cash burn Starlink revenue debt` | failed | `http_status` | 0 | same |
| pp-spacex | (hydration) | ok | none | 3 | - |

**Zero index records.** Consequently the four standing `web_search` per-record codes
(`native_identity_unknown`, `unknown_publication_time`, `engagement_unavailable`,
`target_not_hydrated`) did not appear - their absence is arithmetic, not a sign of cleaner recall.

Three Wikipedia hydrations succeeded (`SpaceX`, `Lock-up_period`, `Short_(finance)`), all K0 /
`wikimedia` / `representation_kind=page`, with `exact_content_hash`, `observed_at`, and the four
required attributes (`content_type`, `link`, `requested_url`, `final_url`). No redirects. **`title`
was empty on all three and no `field_omitted` was attached** - a real vocabulary miss. `edges: 0`,
because discovery produced nothing to name. These records are definitional context and carry no
sentiment signal.

**The structural ceiling, verified in source** (`adapters/public_page.py:114`): `PAGE_SELECTIONS` is a
closed two-row table - `article:<Wikipedia_title>` and `control`. A value carrying `:`, `/` or `\` is
refused as `unselected_target` *before any call*. So **no news article, analyst note or press page
discovered by DDG can ever be hydrated by this package.** `target_not_hydrated` here is not a budget
gap; it is the ceiling.

### L4 - Reddit through the web index (the intended recall workaround)

| step | query | outcome | loss | kept |
|---|---|---|---|---|
| ws-reddit-ticker | `site:reddit.com SPCX stock` | failed | `http_status` (202) | 0 |
| ws-reddit-camps | `site:reddit.com SpaceX stock lockup short squeeze cash burn` | failed | `http_status` (202) | 0 |
| ra-from-index | - | **NEVER RAN** | - | - |

Step B was structurally unconstructible from an empty selection - a hydration step forbids running on
nothing, so an empty K4 answer **terminates the lane** rather than degrading to a weaker K3 read.

The separation this lane existed to produce - "the archive does not hold it" vs "it isn't there",
available because a DDG hit *proves* a thread exists and `archive_lag` is emitted by nothing in the
delivery - **was not produced**, because there was no proven-existent target to point the archive at.

What the 202 does and does not license: `unreachable` was not attached (the read answered, so
something took it); `network_intercepted` was not attached (no interception signature, captive-portal
caveat not invoked); `schema_drift` was not attached (the parser never got a body it read as an
answer). The package cannot class 202 further than `http_status`, so whether DDG or an appliance in
front of it produced it is unresolved. Artifact outcome is `failed`, **not `empty`** - the distinction
that stops a caller reading it as "nobody discusses SPCX".

**`ddg_html` is the only path in this package from a Reddit query to a Reddit score. With it at 202,
searchable Reddit was closed for this run - not degraded, closed.**

### L5 - X publisher timelines (`x_syndication_timeline`, `x_guest_graphql`)

| step | route | outcome | loss | recv | kept | warning |
|---|---|---|---|---|---|---|
| xs-spacex | x_syndication_timeline | partial | `recall_window_partial` | 20 | 12 | - |
| xs-elonmusk | x_syndication_timeline | partial | `recall_window_partial` | 100 | 12 | - |
| xs-unusual-whales | x_syndication_timeline | partial | `recall_window_partial` | 101 | 12 | - |
| xg-users | x_guest_graphql | **failed** | `auth_required` x3 | 0 | 0 | `UserByScreenName answered 401: the guest token does not authorize this operation` |
| xg-timeline | - | **NOT RUN** | - | - | - | input `rest_id` never arrived; no guessed id used |

- **The 12:12Z 429 did not reproduce at 12:28Z.** Three 200s, no identity change, no retry, no
  fallback. Two observations of this host's channel minutes apart; licenses nothing about X policy.
- **The predicted `field_omitted` on `published_at` did not occur.** All 36 records carry a parsed
  `published_at` and `authoritative` time confidence; 0 records carry any record-level loss. The
  `created_at` spelling the adapter's evidence recorded as unreadable parsed cleanly this run - so a
  future run must re-check rather than inherit this.
- **`x_guest` 401 is `auth_required`, not `stale_identifier`.** Per adapter source a rotated query id
  answers 404; 401/403 is a guest-blocked operation. `GUEST_QUERY_ID_RECOVERY` did not ride as a
  warning. This was `x_guest`'s first ever smoke on this host and it **contradicts the package's own
  2026-08-10 evidence of `UserByScreenName` at 200.**
- **The cap artifact is worse than the cap.** 221 entries offered, 36 kept. For @elonmusk (100
  offered) and @unusual_whales (101 offered) the first 12 *in native order* are all-time
  top-engagement posts from 2022-2025. Window coverage: **@SpaceX 12/12 in-window, @elonmusk 1/12,
  @unusual_whales 0/12** (earliest kept post 17 days before the window opens).
- **Ordering degeneracy, derived not assumed.** Every `EngagementSnapshot.observed_at` is
  12:28:00-12:28:05Z, after the frozen `as_of` of 12:00:00Z. `ordering.eligible_snapshot` admits only
  observations at or before `as_of`, so **0 of 36 records had an eligible `reply_count` snapshot.**
  `most_replied` silently degraded to chronology and `order_records` raised nothing.

**Zero of 36 records mention SPCX or SpaceX equity.** The 13 in-window records are Falcon 9 launch
operations, Globalstar 2-R deployment, USSF-366, droneship landings, one Musk post about Grok 4.6, and
one company-update video ("We made rockets reusable and are rebuilding the internet in space...",
22,088 favs / 2,944 rt / 1,015 replies / 579 quotes). Across all 36 bodies, exactly one string matched
`/spcx|stock|ipo|valuation|share price|invest/i` - a 2023-05-02 unusual_whales post about a
congressional stock-trading bill, unrelated to SpaceX.

**`x_search` is deferred** (the `SearchTimeline` query id is unrecovered behind an ESM import map), so
this lane measures **publisher voice only** and cannot speak to audience sentiment at all.

### L6 - YouTube, plus the attestation disambiguation

| step | operation | outcome | loss | kept |
|---|---|---|---|---|
| yt-search-ticker | search | partial | `recall_window_partial` | 8 of 20 |
| yt-search-camps | search | partial | `recall_window_partial` | 8 of 17 |
| yt-player | player | **failed** | `attestation_required` x4 | **0** |
| yt-comments-a/b | next (hydration) | empty | **none** | 0 |
| yt-comments-a/b-disc | next (discovery) | empty | **none** | 0 |

**Attestation verdict: cause 2 established.** `attestation_required` is real for `player` on this
host; the 12:12Z probe target was not stale. Procedure: `search` answered 200 and parsed 37 rows,
proving route + published web key + `CLIENT_VERSION = "2.20260808.00.00"` live *independently of
playability*. Then all four fresh ids taken from that same search minutes earlier returned playability
`UNPLAYABLE` / reason `Video unavailable`:

| target | playability | reason |
|---|---|---|
| `player:ggdyD2Un5zo` | UNPLAYABLE | Video unavailable |
| `player:db_VTcbHEeU` | UNPLAYABLE | Video unavailable |
| `player:aXW0frj4iy0` | UNPLAYABLE | Video unavailable |
| `player:_r-F0J-Uf60` | UNPLAYABLE | Video unavailable |

Two corrections the worker made to its own dispatch, both load-bearing:

1. `attestation_required` carrying metadata anyway is true **only** of the caption case on an `OK`
   player. For a playability refusal `_player_page` routes to `_failed` before touching `videoDetails`
   by explicit design ("a response the origin declares unplayable is not mined for the metadata it
   happens to carry"). Step B yielded **zero records**.
2. Therefore `date_precision_only` "certain on Step B" did not and **could not** occur - `publishDate`
   was never reached.

**Comments: nothing, through either step shape.** The hydration shape structurally cannot reach a
comment: `runner.py:321` is
`return step.kind == "discovery" and bool(page.cursor_out) and kept < step.max_items` - a hydration
step never spends a cursor, by design. Re-run as `kind: "discovery"` with `query: "next:<videoId>"`
(disclosing the lost lineage), the continuation *was* spent (`pages: 2`) and the second call answered
"carrying no continuation token and no thread". **Both videos, both shapes, nothing.** The adapter
types this `empty` with **no loss code at all**, because comments-disabled answers identically - the
exact case `protocol.md` says a caller cannot distinguish from "there is nothing there".

16 search records, all with `published_at` empty, `time_confidence unknown`, `engagement []`:

| pos | id | title | channel | viewCountText | publishedTimeText |
|---|---|---|---|---|---|
| 0 | `ggdyD2Un5zo` | SpaceX Just Crushed Earnings. Why Is the Stock Falling? SPCX | UNRIVALED INVESTING | "21,068 views" | "12 days ago" |
| 1 | `db_VTcbHEeU` | SPCX Earnings: Fundamentals Correction Ahead? | Schwab Network | "27,055 views" | "13 days ago" |
| 2 | `aXW0frj4iy0` | SpaceX Stock Crash Over? Major Buy Signal Incoming To SPCX | Crypto Jebb | "5,443 views" | "5 days ago" |
| 3 | `7lOJLymVMjs` | The Tesla Flying Roadster Launch Event & SPCX Merger Price | Meet Kevin | "39,911 views" | "2 days ago" |
| 4 | `5R33qOJOGvI` | SPACEX STOCK PRICE PREDICTION - EVERYTHING JUST CHANGED! | Stock Moe | "13,670 views" | "4 weeks ago" |
| 5 | `eJ4aLwK368M` | SpaceX Will Create Millionaires... But Not Until THIS Happens | Ross Givens | "159,445 views" | "3 weeks ago" |
| 6 | `vFMIpvg7Wpw` | SPACEX STOCK PRICE HAMMERED! TIME TO BUY? | Austin Talks Investing | "2,500 views" | "10 days ago" |
| 7 | `Huv4D-yTwlg` | 3 Reasons Why SpaceX Stock Is Finally A Buy | Hedged Stock Income | "8,316 views" | "9 days ago" |
| 0 | `3IQXBMfIHRU` | The SpaceX IPO Explained in 90 Seconds (Bull + Bear Case) | Boysminem | "299 views" | "2 months ago" |
| 1 | `_r-F0J-Uf60` | SpaceX Earnings: The Bear Case Nobody's Talking About | Ricky Gutierrez | "10,623 views" | "12 days ago" |
| 2 | `S8UnMvLT4sY` | Ark Investment's Sam Korus shares his bull case for SpaceX | CNBC Television | "5,045 views" | "1 year ago" |
| 3 | `LRrrDIHOt00` | SpaceX Bull and Bear Cases, Part 1 | Money News Network | "2,710 views" | "2 weeks ago" |
| 4 | `zZSFDOqE4L4` | SpaceX Bull and Bear Cases, Part 2 | Money News Network | "2,482 views" | "2 weeks ago" |
| 5 | `5PZDHG2ysD8` | SpaceX Squeezes Up Near IPO, Fiber Breakouts $AAOI $LITE, $SPCX | Bear Bull Traders | "5,908 views" | "Streamed 6 days ago" |
| 6 | `_NRg47lxqR0` | SpaceX IPO 'Will Be Volatile' Says Ark Invest's Cathie Wood | Bloomberg Podcasts | "194,727 views" | "3 months ago" |
| 7 | `pl8E1CgzoQ0` | Capex Is Only Way to Musk's AI Vision for SpaceX, Says Dan Ives | Bloomberg Television | "29,275 views" | "12 days ago" |

Two Shorts carried a different locator shape (`/shorts/<id>`), the rest `watch?v=<id>&pp=<b64 query>`.

**`rss_atom` is unusable here**, verified at `adapters/rss_atom.py:424`: it takes a `channel_id` and
the one declared route is `feeds/videos.xml?channel_id=`. Nothing in the package produces a `UC...`
id - `_search_record` sets `author` from `ownerText`, a display name. No id was guessed.

**Captions are deferred** (`youtube_captions`, PoToken/BotGuard; `captionTracks` empty across five
clients on three videos). So there is no video content in this lane at all - only titles.

## 4. Composition totals

| lane | records | usable for the question |
|---|---|---|
| L1 Reddit feeds (+ re-dispatch) | 74 feed + 1 hydrated | **1** (with engagement) |
| L2 Hacker News | 68 | **17 in-window on-topic; 3 with any engagement signal** |
| L3 open web | 0 index + 3 Wikipedia | 0 |
| L4 Reddit via index | 0 | 0 |
| L5 X | 36 | 0 on-topic |
| L6 YouTube | 16 titles | 16 titles, 0 engagement integers, 0 comments |
| **total** | **~198** | **4 records with any engagement signal** |

Typed losses observed: `http_status` (202, x5 queries, 3 independent measurements),
`rate_limited` (429, x3), `auth_required` (401, x3), `attestation_required` (x4),
`recall_window_partial` (widely), `engagement_unavailable` (standing),
`third_party_archive` (standing), `unselected_target` (structural ceiling).

Never observed: `schema_drift`, `malformed_json`, `unreachable`, `network_intercepted`,
`stale_identifier`, `field_omitted`, `withheld`, `date_precision_only`,
`discovery_not_recorded`, `archive_lag`, `scope_required`.

## 5. The delivered answer

**None.** The composition's honest output was: this package cannot answer whether SpaceX sentiment is
up or down, and here is the typed evidence for each reason. Every worker declined to rank, judge or
characterize sentiment, as `SKILL.md` requires.
