# super-research bakeoff: defects, differences, and the improvement roadmap

Part 3 of 3, and the entry point. Read this first.

- Part 1 - run 1 data: [REVIEW-2026-08-17-bakeoff-run1-last30days.md](REVIEW-2026-08-17-bakeoff-run1-last30days.md)
- Part 2 - run 2 data: [REVIEW-2026-08-17-bakeoff-run2-super-research.md](REVIEW-2026-08-17-bakeoff-run2-super-research.md)
- Part 4 - run 3, after this roadmap was executed: [REVIEW-2026-08-17-run3-superset.md](REVIEW-2026-08-17-run3-superset.md)

Date: 2026-08-17. Both runs asked the same question ("SpaceX sentiment - do people think it will go
up or down?") over the same window (2026-07-18 to 2026-08-17) on the same host, with Opus 5 on the
planner and all workers for run 2.

**Target state for `super-research`:** a superset of `last30days`, `agent-reach` and comparable
deep-research scraping tools, optimized for **speed and quality** simultaneously. This document is
written as input to that work, not as a postmortem.

---

## 1. The one-line diagnosis

**`super-research` discovers competitively and hydrates almost nothing.**

That is the whole finding, and it is measurable per platform:

| platform | super-research discovery | super-research hydration | last30days |
|---|---|---|---|
| YouTube | **16 titles** (better) | **0** engagement integers, 0 comments, 0 transcripts | 7 videos, 240,603 views, 7,074 likes, 2 transcripts |
| Hacker News | 62 rows | 16 points total across 4 stories; **no comment engagement exists on the surface at all** | 13 stories, 571 points, 592 comments |
| Reddit | 74 feed rows (~1-3 days deep) | **1** score (874/89) | 20 threads, 14,432 upvotes, 3,462 comments |
| X | 36 posts | 0 on-topic | 0 (unauthenticated) |
| open web | 0 (202) | structurally impossible - closed 2-row table | 14 sources via host WebSearch |
| prediction markets | **route does not exist** | - | queried, 0 after filtering |

Run 2 returned ~198 records of which **4 carried any engagement signal**. Run 1 returned 58 items,
nearly all weighted, in 92.4 seconds from a single context. Run 2 cost **~1.4M subagent tokens across
8 agents and ~45 minutes** and did not answer the question.

The problem is not finding things. It is reading them, and doing it in parallel.

## 2. Where the 1.4M tokens actually went

This is the most important structural observation in the report.

`protocol.md` §Manifest grammar states: *"Nothing runs concurrently; the ledger's placement model is
`ledger.schedule_of`'s."* The runner is serial across 18 route surfaces, with `min_interval_ms=30000,
burst=1` on `reddit_feed`.

**So I bought parallelism at the orchestration layer instead.** The only reason run 2 finished in 45
minutes rather than hours is that I split it into six independent lane agents that each drove a serial
runner against a different origin. Every one of those 1.4M tokens was spent purchasing concurrency the
runner declines to provide, plus the planning and reporting overhead that comes with six contexts.

Pacing is per-origin. Cross-origin concurrency is therefore safe and does not weaken any guarantee in
the protocol - not the frozen replay, not the per-step authorization model, not the ledger. A single
agent driving a concurrent runner across distinct hosts would have produced the same artifact set for a
small fraction of the cost.

**Recommendation R-1 (highest payoff in the document): make the runner concurrent across distinct
origins, keeping strict serialization and pacing per origin.** Everything else in this report is
secondary to this.

## 3. What to keep - the spine is correct

Do not trade these away for recall. They are what `last30days` cannot do, and they earned their keep
in this run:

1. **Typed loss as the finding.** Run 1's entire diagnostic was `Research quality: 4/5 core sources.
   Missing: X/Twitter.` Run 2 distinguished a 202 channel rejection from an absence of coverage, a 401
   authorization refusal from a 404 rotated identifier, and a host attestation failure from a stale
   probe target. Each was actionable; run 1's was not.
2. **The access ladder, with no capability depending on K5.** The one Reddit number produced carries
   `access_class: K3`, `operator: arctic-shift`, `time_confidence: reported`, `loss:
   ['third_party_archive']`. Run 1's 14,432 upvotes carry no such labelling and cannot distinguish
   "the platform said this" from "an archive said this".
3. **`discovery` != `hydration`, and `representation_kind` partitioning every grouping key.** A search
   hit can never merge into the target it discovered. This directly caught a real hazard: 3 HN stories
   each legitimately appeared twice, once per representation, and deduping by `native_item_id` would
   have silently collapsed them.
4. **Frozen `as_of` replay.** Worth keeping, with the eligibility fix in D-11.
5. **No fallback, no retry, no changed identity on a 429.** Held under pressure in three lanes.
6. **Exact native integers only in `engagement`; the route's own strings in `attributes`.** This is why
   `"21,068 views"` never became a number. Run 1 would have used it.
7. **The refusal to rank, judge, or synthesize.** Kept the workers honest about a null result instead
   of manufacturing a directional read from four weighted records.

## 4. What run 2 found that run 1 missed

Discovery breadth is genuinely competitive, and two records prove it:

- **`r/StockMarket`: "Nvidia discloses $21 billion stake in SpaceX at end of second quarter"** - 874
  score, 89 comments, 2026-08-15. Materially relevant to the directional question. Absent from all 8
  of run 1's clusters.
- **HN `49061408` (groby_b), in-window: "almost 50% of the float is loaned out"**, naming the earnings
  call as catalyst. The best market-mechanics record in either run. It contains **no SpaceX token**, so
  it never appeared in super-research's own discovery set and every lexical filter classed it silent -
  it exists only because two extra `item:` hydrations were authorized.
- **Bloomberg Television's Dan Ives segment and Bloomberg Podcasts' Cathie Wood segment**, plus Schwab
  Network and Ricky Gutierrez's bear case - analyst voices run 1 never surfaced.

And three attribution traps a scoring pipeline papers over:

- **HN `49189113`** carries the largest engagement figure in the lane (138 points, **282 descendants**)
  and is a story about an X product exec stepping down - no SpaceX token, no market term. A lockup
  remark sits inside as an aside. Weighting that comment by its thread attributes 282 comments of
  unrelated argument to SPCX sentiment.
- **`search_by_date:SPCX` matched the authors `SPCECDET` and `spixy`**, and 27 of 56 comment bodies
  never contain the token. Row count on a ticker query is not topic volume.
- **Bare-alternation term lists inflate matches.** Reproduced: `"Just wanted to share my DD on this"`,
  `"Analyst calls the top"`, `"Musk puts pressure on suppliers"`, `"Re-evaluation of the thermal
  model"` all match unbounded; none survive word-boundary + stem pruning.

Run 1's relevance floor dropped **84, 124, 147 and 21** off-topic Reddit posts across four subqueries.
That is why it is fast and clean. It is also unauditable, and this run demonstrates the error class it
could be committing silently.

---

## 5. Defect register

Ranked by impact on answering a sentiment question. Each has evidence in part 2.

### P0 - route coverage. These are why run 2 could not answer.

| id | defect | evidence | fix direction |
|---|---|---|---|
| **D-1** | **No Reddit search route.** Only `arctic_shift_posts_ids` (hydration by exact id) ships. `posts/search`, `comments/search`, and `comments` by `link_id` are specified but unshipped. **No Reddit comment route exists at all**, so comment-level sentiment - the densest surface for this question - is unreachable. | L1 Step B made zero calls; the 1,265-upvote r/stocks lockup thread (Aug 5) is unreachable because `reddit_feed` spans 1-3 days | Ship the three Arctic Shift routes. Emit `scope_required` where the grammar needs `subreddit`/`author`. Add a Reddit comment route |
| **D-2** | **No X search.** `x_search` deferred on an unrecovered `SearchTimeline` query id. Every X read is one named handle's timeline. | 36 records, **0 on-topic**; lane can only measure publisher voice | Recover the query id, or add a K4 index->hydrate path for X, or declare a K5 throughput upgrade |
| **D-3** | **No press page can ever be hydrated.** `public_page.PAGE_SELECTIONS` is a closed two-row table (`article:<Wikipedia_title>`, `control`). Any locator with `:`/`/`/`\` is refused as `unselected_target` before any call. | L3: 3 Wikipedia records, 0 press; `adapters/public_page.py:114` | Add an open-locator `web_page` hydration route that accepts a discovered `normalized_locator`, with an https-only / read-only policy |
| **D-4** | **Single K4 provider.** `ddg_html` is the only web-index route, so one 202 closed both L3 and L4 - and with them the only path from a Reddit query to a Reddit score. | 202 on 5 queries, 3 independent measurements | Declare Brave / Exa / Serper / Parallel as **parallel planned routes**, not fallbacks (preserves the no-fallback law). Add a host-native-search delegation hook, as `last30days` does with `LAST30DAYS_NATIVE_SEARCH=1` |
| **D-5** | **No captions, so no video content.** A 20-minute bull thesis is a title. | L6: 16 titles, 0 transcripts | Add a local-binary route class (`yt-dlp`), which is how `last30days` gets transcripts keylessly |
| **D-6** | **No TikTok / Instagram search.** `tiktok_public` unverified; `instagram_public` is profile-only. | roster | Ship search surfaces; consider K5 throughput upgrade |
| **D-7** | **No prediction-market route at all.** For a literal "up or down" question, market odds are the highest-signal evidence available, and the roster has no such adapter. | absent from `runner.surface_descriptors` | Add a K0 Polymarket/Kalshi adapter. `last30days` has one |
| **D-8** | **No finance-native surface.** No Stocktwits or equivalent. | absent from roster | Add if equity sentiment is in scope |

### P1 - speed

| id | defect | evidence | fix direction |
|---|---|---|---|
| **D-9** | **Nothing runs concurrently.** Serial runner across 18 surfaces, 30s pacing on `reddit_feed`. | `protocol.md` §Manifest grammar; run 2 took ~45 min and 1.4M tokens to buy cross-origin parallelism at the agent layer | **R-1.** Concurrency across distinct origins; strict serialization and pacing per origin |
| **D-10** | `x_guest` spends two origin calls per read (activation + GraphQL). Unclear whether the minted token is reused across steps in one run. | L5 warning text; `pages: 3` for 3 hits | Verify activation caching within a run; document it |
| **D-19** | The `discovery_not_recorded` false-alarm hazard forces every discovery->hydration pair to be **staged**, doubling agent round trips, because only `web_search` emits `representation_kind: index`. | planner rule R2; `normalize.type_discovery_gaps` | Scope the gap check to artifacts that actually contain index records, so fused non-index pairs are safe |

### P2 - silent failure and correctness

| id | defect | evidence | fix direction |
|---|---|---|---|
| **D-11** | **Counted orders degrade silently.** When `as_of` predates observation, `ordering.eligible_snapshot` returns `None` for every record, so `most_commented` / `most_replied` return chronology and **`order_records` raises nothing**. | Confirmed independently by L2 and L5. `eligible_snapshot(r,"descendants","...12:00:00Z") -> None` vs `...12:30:00Z" -> EngagementSnapshot(descendants,1,...)`. L2's `most_commented` output was byte-identical to `newest` | Raise `OrderingError`, or attach a typed loss, when a counted view finds zero eligible snapshots. Document that a frozen `as_of` must be at or after observation time, and that a second labelled ordering horizon can be applied post hoc with zero re-acquisition |
| **D-12** | `reddit_archive` and `reddit_feed` declare **neither** `comment_count_metric` nor `reply_count_metric`, though `num_comments` rides as a snapshot on every archive record - so `most_commented` is unusable on the one Reddit surface that has counts. | `runner.surface_descriptors`, read back offline | Declare the metric names |
| **D-13** | **An empty YouTube comment section carries no loss code**, because comments-disabled answers identically to a withheld payload - the exact case `protocol.md` says a caller cannot tell from "there is nothing there". | L6: both videos, both step shapes, `empty` with no loss, while the same client is refused `player` on 4 fresh ids | Add a vocabulary code distinguishing a withheld payload from a disabled feature, or at minimum type the client-refusal case |
| **D-14** | `archive_lag` and `scope_required` are documented but **emitted by nothing**, so an archive coverage gap on a recent window arrives as a bare `empty`. | `protocol.md` says so explicitly | Ship them with D-1's routes |
| **D-15** | `public_page` returned an **empty `title` on all three records with no `field_omitted`** attached. | L3 | Attach the code, or remove `title` from that route's declared row |
| **D-16** | **Multi-hit hydration steps starve later hits.** `runner.run_step` tests the cap at the top of each call and breaks, so with one high-yield call the remaining hits are never called - silently. | planner rule R1, derived from source before any run | Per-hit budgeting, or a declared per-call yield so a planner cannot under-cap |
| **D-17** | **Native order is not recent order.** A cap against `x_syndication`'s native ordering returned 2022-2025 all-time-top posts. Window coverage: @SpaceX 12/12, @elonmusk 1/12, @unusual_whales **0/12**. | L5 | Declare each surface's ordering guarantee; support a window filter applied *before* the cap so budget is spent in-window |
| **D-18** | `reddit_feed` makes exactly one call and never pages, so any `max_items` below the page size is **pure recall loss at zero cost saving**. | Confirmed empirically: at 8 it dropped 17 per subreddit and emitted `recall_window_partial`; at 25 it kept all 25 with no loss, same single read | Adapters declare their page size; cap defaults to it |

### P3 - caller ergonomics (the "quality" half)

| id | defect | evidence | fix direction |
|---|---|---|---|
| **D-20** | **No topical relevance helper.** The caller hand-writes lexical rules, and bare alternations inflate matches in a way indistinguishable from signal. | 4 reproduced false positives; L2 introduced 2 of its own and caught them only by reading every match | Ship a word-boundary + stem-pruned matcher, or a relevance projection in `project`. This is the auditable counterpart to `last30days`' invisible relevance floor |
| **D-21** | Nothing warns against **weighting a comment by its parent thread's engagement**. | HN `49189113` would have attributed 282 unrelated comments to SPCX | Document the rule; consider refusing to expose a parent's engagement on a child record |
| **D-22** | **A token match is not a topic match**, and loose index matching is unsurfaced. | `SPCX` matched authors `SPCECDET`, `spixy`; 27/56 bodies lacked the token | Surface which field matched, or attach a code for index-side loose matching |
| **D-23** | No cross-source clustering or synthesis-ready evidence block. Correct by design, but it means six lanes of manual reading where `last30days` hands back ranked clusters. | this run | Keep the acquisition/synthesis split, but supply the calling lane a documented projection + join recipe so the cost lands once, in the library, not per-run |

### P4 - orchestration (orchflows-level, surfaced by this composition)

| id | defect | evidence | fix direction |
|---|---|---|---|
| **D-24** | **Planner staleness.** I dispatched the six lane workers directly, so the planner never learned lanes 3-6 had completed. It spent its last two turns (~470K tokens) issuing rulings, reallocating a budget ceiling and "holding" lanes that had finished 40 minutes earlier - while remaining the authority two live workers obeyed. | planner's final return | A planner that issues binding rulings must be the dispatcher, or must be fed every completion. Make this an orchestration law |
| **D-25** | **Shared scratchpad, generic filenames, cross-lane clobbering.** Two independent incidents: L5 overwrote L1's `stepA.json`; L6 destroyed L2's 62-record discovery set via `step_a.json`. | both workers reported it; file inspection confirmed `stepA.json` held the L5 manifest verbatim | Lane-private directories by convention. Note: initially misread as possible injection because the harness's external-change reminder reads like a directive - it was a plain collision, and my dispatch caused it |
| **D-26** | No shipped **manifest-on-disk verification** helper. | a worker invented one: re-reads the manifest, checks `manifest_id`, `as_of`, step count, `adapter_id`, `query`, `max_items`, `kind`, empty `selected_hits` against command-line values, and aborts before any transport call on mismatch - never repairing | Ship that guard. It is the single most reusable artifact this exercise produced |

---

## 6. Roadmap

Ordered by payoff per unit of work.

**Tier 1 - unblocks the tool for sentiment work**
1. **D-9 / R-1** concurrent runner across distinct origins. Largest single win; makes everything else affordable.
2. **D-1** ship the three Arctic Shift routes plus a Reddit comment route. Reddit is where retail sentiment lives and it is currently unreachable beyond 1-3 days.
3. **D-4** multiple K4 providers as parallel planned routes, plus host-native-search delegation.
4. **D-3** open-locator `web_page` hydration so a discovered press page can be read.

**Tier 2 - closes the quality gap vs `last30days`**
5. **D-11** make counted-order ineligibility loud, and document the post-hoc ordering horizon.
6. **D-5** local-binary route class for captions/transcripts.
7. **D-7** prediction-market adapter.
8. **D-20** shipped relevance matcher, so the caller stops hand-rolling regexes that inflate.
9. **D-17 / D-18 / D-16** cap and ordering hygiene: declared page sizes, declared ordering guarantees, window-before-cap, per-hit budgets.

**Tier 3 - vocabulary and coverage completeness**
10. **D-13 / D-14 / D-15** ship the missing loss codes; nothing should return a bare `empty` that a caller cannot interpret.
11. **D-2 / D-6 / D-8** X search, TikTok/Instagram search, finance-native surface.
12. **D-19** scope the `discovery_not_recorded` check so fused pairs are safe and round trips halve.

**Tier 4 - orchestration law**
13. **D-24 / D-25 / D-26** dispatcher-owns-rulings, lane-private scratchpads, ship the manifest guard.

## 7. Bottom line for the next session

`super-research`'s discipline is the right foundation and should not be softened to chase recall. Its
deficit is **route coverage and a serial runner**, not design. It is a correct provenance spine with
too few routes attached, executed one call at a time.

`last30days` is the inverse: broad route coverage and real speed with no provenance, an unauditable
relevance floor, and no way to tell "nothing there" from "refused".

The merge target is explicit: **super-research's spine + last30days' route roster + concurrency across
distinct origins.** Tier 1 alone would have let run 2 answer the question - and at a fraction of 1.4M
tokens, because most of that spend was buying parallelism the runner should provide itself.

Two library findings from this run remain **unfiled** through `scripts/friction.py`, pending a decision:
the silent counted-ordering degradation (D-11) and the untyped empty-comment gap (D-13).
