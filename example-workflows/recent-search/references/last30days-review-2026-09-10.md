# Upstream technique review — 2026-09-10

The review fixes [last30days-skill v3.24.0](https://github.com/mvanhorn/last30days-skill/tree/ca9d415e66073b17702f385d6886934097aec0e7),
commit `ca9d415e66073b17702f385d6886934097aec0e7` (2026-09-09).
The relevant implementation lives in [skills/last30days/scripts/lib/](https://github.com/mvanhorn/last30days-skill/tree/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib).
This is a source review, not a claim that every upstream backend was run.
The selected techniques informed independently authored changes to this
keyless, explicitly planned, bounded-read package.

## Technique inventory and disposition

| Upstream technique / source files | Decision and evidence boundary |
| --- | --- |
| Reddit RSS global/subreddit search and new/hot/top listings ([lib/reddit_rss.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/reddit_rss.py), [lib/reddit_keyless.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/reddit_keyless.py)) | Adopt global search through `reddit_feed` → `search:<query>`, preserving Atom IDs, dates and missing engagement. Existing subreddit feed plus Shreddit scoped search/listings cover the other question types. RSS sort/window variants are not claimed as measured here; search uses `sort=new`, one page and client filtering. |
| Reddit Shreddit HTML search/listing and selected post/comment enrichment ([lib/reddit_shreddit.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/reddit_shreddit.py), [lib/reddit_listing.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/reddit_listing.py)) | Existing parity: explicit global/scoped search, listing and selected comments, canonical identity and depth planning. No JSON identity-switch ladder or automatic retries. |
| Arctic Shift batched ID hydration and post search ([lib/reddit_arctic.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/reddit_arctic.py)) | Existing selected-ID hydration retained. Adopt one-page, scoped post search with origin `after`/`before`; require subreddit or author, allow title, reject unknown/repeated parameters. Retain operator labels and typed 422 throttling. No unscoped expensive title scan, comment search, automatic source substitution or completeness claim. Per-hit hydration retains provenance rather than silently batching caller identities. |
| DuckDuckGo, Startpage, configured SearXNG ([lib/web_search_keyless.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/web_search_keyless.py)) | Existing DDG HTML, Bing web/news RSS and Google News RSS supply explicit web discovery. Startpage live read returned Anubis; adding an unmeasured parser would not improve usable coverage. Configured SearXNG hosts need an independently admitted origin contract. No implicit fallback ladder. |
| Jina Reader URL-to-Markdown/cache ([lib/web_fetch_keyless.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/web_fetch_keyless.py)) | Existing explicit `open_page` captures selected public pages and source provenance. A generic third-party URL proxy would hide target-origin boundaries; defer until its target validation, cache time and operator loss are admitted. This is not equivalent coverage of JavaScript-only pages. |
| HN Algolia search and comment tree ([lib/hackernews.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/hackernews.py)) | Existing Algolia discovery/item tree and Firebase item routes provide parity with selected depth and exact native counts. |
| GitHub issue/PR search, repository context and comments ([lib/github.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/github.py)) | Existing public REST repository/search/issues/releases cover the reusable keyless core. Do not adopt automatic `gh`/environment token discovery. Broad comment/README enrichment remains a caller-planned extension, not claimed full parity. |
| Bluesky authenticated search ([lib/bluesky.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/bluesky.py)) | Keep existing public AppView search/author feed. Exclude app-password/session acquisition; no user credential is needed by the shipped route. |
| YouTube discovery, metadata, captions, comments ([lib/youtube_yt.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/youtube_yt.py)) | Existing public client/player, search, next/comment and timed-text operations cover these evidence shapes. Do not add yt-dlp, SSH execution, client-switch retries, cookie import or paid backup. Language-specific transcript fallback remains explicit future work. |
| arXiv through a CLI ([lib/arxiv.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/arxiv.py)) | Existing direct arXiv Atom query plus OpenAlex/Crossref cover scholarly discovery without a new CLI dependency. |
| Stocktwits public streams and symbol lookup ([lib/stocktwits.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/stocktwits.py)) | Existing routes provide parity. Sentiment aggregates belong in cited analysis, not acquisition; no invented cross-platform ratios. |
| Polymarket Gamma search and market prices ([lib/polymarket.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/polymarket.py)) | Existing Gamma plus Kalshi/Manifold routes retain native price strings. Query expansion remains explicit input; resolved-market selection belongs in the report contract. |
| Techmeme public archive via CLI ([lib/techmeme.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/techmeme.py)) | Defer dedicated curation adapter: external CLI dependency and no measured native payload here. Web discovery can find these pages but does not prove equivalent archive coverage. |
| Digg curated clusters and embedded X quotes via CLI ([lib/digg.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/digg.py)) | Defer dedicated adapter for the same measurement/dependency reasons. A curator quoting a tweet is secondary evidence and cannot establish a fresh native X count. |
| X APIs and bridges ([lib/x_api.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/x_api.py), [lib/xai.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/xai.py), [lib/xquik.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/xquik.py), [lib/bird.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/bird.py), [lib/xurl.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/xurl.py)) | Exclude user bearer keys, paid APIs and cookie/session extraction. Existing public syndication, guest and FxTwitter remain explicit alternatives with their own losses. User-requested xcancel is separately added below; it is absent from this fixed upstream source. |
| LinkedIn/Instagram/TikTok/Threads/Pinterest/Telegram | Upstream ScrapeCreators-backed acquisition requires a key. Exclude it; existing public LinkedIn, Instagram and TikTok routes retain their measured limited fields. No new native Threads/Pinterest/Telegram coverage is claimed. |
| Truth Social, Xiaohongshu, Amazon, Trustpilot | Exclude bearer-authenticated, logged-in MCP, paid proxy or harvested token/browser challenge techniques. These do not satisfy the package's keyless acquisition boundary. |
| Query normalization and fan-out ([lib/query.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/query.py), [lib/fanout.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/fanout.py)) | Retain caller-frozen questions and audited relevance partitioning. Existing fused execution serializes each origin and bounds concurrent lanes. Do not silently rewrite compound questions or lose unsuccessful branches. |
| Near-duplicate similarity and weighted rank fusion ([lib/dedupe.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/dedupe.py), [lib/fusion.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/fusion.py)) | Retain exact identity dedupe, native/index separation and explicit discovery–hydration edges. Similar text, author caps and cross-platform scoring must not merge contradictory observations or promote secondary counts. Ranking can be a separately declared analysis choice. |
| Freshness validation ([lib/freshness.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/freshness.py)) | Adopt the operational principle through explicit period/window, `as_of` after reads, per-record observation times and selected hydration. A changed metric requires a fresh explicit read; model assertions do not certify it. |
| HTTP/cache/retry substrate ([lib/http.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/http.py), backend selection) | Existing cache, origin pacing, request limits, typed failures and fixed routes supply parity for bounded read mechanics. Exclude repeated retries, credential escalation and automatic fallback. |
| Saved-library feed rendering ([lib/feed.py](https://github.com/mvanhorn/last30days-skill/blob/ca9d415e66073b17702f385d6886934097aec0e7/skills/last30days/scripts/lib/feed.py)) | Not acquisition: it renders already-held records. No new adapter is appropriate. |

## Xcancel: implemented shape, live limitation

`x_xcancel` supports `search:<query>` and selected `status:<handle>/<id>`
(also the exact canonical `https://x.com/<handle>/status/<id>` produced by
`coverage.plan_depth`). Both read only `https://xcancel.com`, once per page;
there is no challenge execution, cookie import, alternate host or retry.
Records identify X content while naming operator `xcancel` and
`third_party_archive`. Selected status reads discard other timeline posts.
Quoted posts are excluded from the parent's body/counts. Exact integers are
kept; abbreviated numbers remain source strings, and missing counts stay unknown.

Markup was derived from public Nitter's
[tweet renderer](https://github.com/zedeus/nitter/blob/376f14908e27e095049bbbeb648e742501144010/src/views/tweet.nim)
and [timeline renderer](https://github.com/zedeus/nitter/blob/376f14908e27e095049bbbeb648e742501144010/src/views/timeline.nim).
The positive fixture [skills/research-acquire/tests/fixtures/recent_routes/nitter_source_derived.html](../skills/research-acquire/tests/fixtures/recent_routes/nitter_source_derived.html)
is synthetic source-derived markup, **not a successful live capture**.
The source's `tweet-date` anchor carries the full UTC date, and `tweet-stat`
icons identify count kinds. Live parser compatibility and pagination remain
unverified until an ordinary public request yields usable content.

## Live observations

One bounded urllib GET per URL, fixed identity, no redirects/retries/challenge
interaction, 20-second timeout, 1.5 MB ceiling, observed 2026-09-10 UTC:

| UTC | Origin request | Observation |
| --- | --- | --- |
| 15:27:44 | `https://xcancel.com/search?f=tweets&q=python` | HTTP 200 browser verification, 11,354 bytes; no tweets. |
| 15:27:44 | `https://xcancel.com/jack/status/20` | Same challenge body and digest; no selected status. |
| 15:27:44 | `https://arctic-shift.photon-reddit.com/api/posts/search?subreddit=python&after=2026-09-08&before=2026-09-10&limit=5&sort=desc` | HTTP 200 JSON, 21,793 bytes; five rows dated September 9, 19:20:35–23:37:07 UTC, within the requested window. |
| 15:27:45 | Same endpoint, `after=2026-08-01&before=2026-08-02` | HTTP 200 JSON, 23,645 bytes; five rows dated August 1, 17:02:54–21:15:25 UTC, within the older window. |
| 15:27:46 | `https://www.reddit.com/search.rss?q=python&sort=new&t=week` | HTTP 200 Atom, 118,134 bytes; confirms search shape, not arbitrary window reach. |
| 15:27:47 | `https://www.startpage.com/sp/search?query=python` | HTTP 200 Anubis challenge, 22,046 bytes; no usable search evidence. |

Xcancel challenge SHA-256:
`95f1bac5ec5d956697cf8e241408ddd11a69da46e6fb1a55ee06649efc67b70b`.
Arctic recent/older digests:
`58f82661c5ce4dcefcbc2db19afc2e22f322640d6a8f741111dbe7a85a083738`,
`be670d93d7e8fdb92bba0c9a1edd940e7056a492c7aeb115b311b07ebeedf60a`.
Reddit RSS digest:
`e5b29f07e04b6b3538c60d51fa2ac4c70097bf24736ee3e594f18785e4049c7a`.
Startpage digest:
`51c2f94838aff7305ef499059f318fd3af995fd3fb222c12f4578edcc89a7b41`.

Arctic Shift's [public API documentation](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md)
supports scoped posts/search with before/after. Archive freshness, ingestion
gaps and complete recall are separate questions from accepting a time bound.

A second observation used the actual shipped `runner.run_acquisition` and its
default paced transport at **15:54:14 UTC**, with three explicitly planned
steps, `cap=5`, September 8–10 window, and `as_of=2026-09-10T23:00:00Z`:

| Route | Actual result |
| --- | --- |
| Arctic Shift search | One page, 46 rows received, five kept; cap produces `recall_window_partial`. Kept dates are September 9, 19:20:35–23:37:07 UTC; all carry `third_party_archive`. |
| Reddit RSS search | One page, 25 entries received, zero kept: all were outside the requested window. `window_capability_unmeasured` remains explicit. This is not evidence that the question has no Reddit answers. |
| Xcancel search | One page, zero rows, `refused` with `attestation_required` and `window_capability_unmeasured`. No further request or challenge interaction. |

The completed acquisition is `partial`, with these three typed losses preserved.
Its serialized artifact SHA-256 is
`69977cda39664f5eac8a2ca5a2628dd4d6841a1baa076d31d26bee6066dbed31`.
The process exited 0 because acquisition completed and reported the refusal;
that exit is not a successful live xcancel smoke. See the committed
[observation summary](live-acquisition-2026-09-10.json) for per-step counts,
dates, locators and losses.

## Contract ownership

The public package owns both evidence and dossier modes. The existing kernel
owns frames, dispatch, pins, artifact identities, isolation and landing;
`orch-research` owns evidence quality; private `research-acquire` owns bounded
reads; `orch-content`/`html-dossier` own report quality. `orch-judge` judges fixed
packets and dossiers against those standards; `orch-do` repairs named findings.
The narrowly scoped migration retires the project acquisition skill, keeps
Python API names, and lets another package call public recent-search with
research semantics. Independent authoring review and the full repository gate
are external acceptance work, not claims made by fixture tests.
