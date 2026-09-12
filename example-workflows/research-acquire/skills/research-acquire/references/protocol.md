# Protocol

The manifest a caller writes, the artifact it gets back, the access ladder every
route is classed on, the loss codes a partial answer carries, the orders a set
may be put in, and how to run a manifest directly. A term in `code` is spelled
exactly as the source spells it. The routine path is the [bounded
plan](acquisition.md); read this for direct runner APIs or manual manifests.

## Manifest grammar

`schema.parse_manifest` validates totally, before any transport call, and
raises `ManifestError` on anything it cannot accept. An unknown key at any level
is rejected.

Manifest keys are exactly `manifest_id`, `as_of`, `steps`.

- `manifest_id` is a nonempty string. `as_of` is an instant spelled
  `YYYY-MM-DDTHH:MM:SSZ` (`schema.INSTANT_FORMAT`); it freezes which engagement
  snapshots are eligible for ordering, so any other spelling is refused.
- `steps` is a nonempty sequence. A repeated `step_id` is rejected, and
  `prior_step_id` must name a step in the same manifest.

Each adapter's steps run as one **lane**, in declared order within the lane;
lanes overlap on a pool of at most `runner.MAX_CONCURRENT_LANES` (8). That is
safe because a step's inputs are frozen in the manifest — a hydration reads the
`selected_hits` the caller froze, never what another lane produced — and
because the governor serializes reads per origin host whatever the lanes do.
`lanes=1` runs the steps serially, for a replay whose timing must match.

Step keys are exactly `step_id`, `kind`, `adapter_id`, `query`,
`prior_step_id`, `selected_hits`, `max_items`, `window_start`, `window_end`.

- `kind` is `discovery` or `hydration`. A discovery step forbids
  `selected_hits` and authorizes one call plus a continuation per page that
  offers a cursor, to `runner.MAX_PAGES_PER_STEP` (5). A hydration step requires
  `selected_hits` and authorizes exactly one call per hit: a page read off a
  cursor was authorized by nobody, which is what keeps a hydration record's
  provenance exact.
- Each hit is `{discovery_locator, target_id}`, both nonempty.
  `discovery_locator` is the normalized locator the caller saw in the discovery
  step's output and is the only thing that ties a hydration record to its
  discovery record; nothing is matched by similarity.
- `max_items` is a required positive cap. On a discovery step it bounds the
  whole step and the core stops once it is met; on a hydration step it bounds
  each authorized call, so the step is bounded by hits × `max_items`. A step
  that truncated, or stopped while the origin still offered, carries
  `recall_window_partial`. A discovery cap under the surface's declared
  `page_size` gets a warning before the read: one call returns the page
  whatever the cap.
- `window_start` and `window_end` are optional instants in the `as_of`
  spelling, `window_start` not after `window_end`. A record the origin dated
  outside the window is dropped before the cap counts it; a record with no
  publication time is kept. The step's warning states how many were dropped.
  Adapters whose origin takes a date bound also send it in the origin's own
  terms: HN Algolia `numericFilters`, Bluesky `since`/`until` on search, Google
  News `when:`, Reddit Shreddit's `t=` bucket, LinkedIn Jobs `f_TPR=`, GitHub
  `created:` and `since=`, YouTube's upload-date search filter, GDELT
  `startdatetime`/`enddatetime`, Stack Exchange `fromdate`/`todate`,
  Wikimedia's date path segments, and the three scholarly origins' filters.
- Whether an operation can bound time at its origin is declared per adapter
  and operation in `runner.WINDOW_REACH`, total over `dispatch.ADAPTER_IDS`. A
  windowed step on an operation declared unable carries `window_not_honored`;
  one on an operation declared but unmeasured carries
  `window_capability_unmeasured`. Both describe the operation's shape, not the
  answer, so an empty in-window answer and an unhonored bound are told apart
  off `loss`.

## The artifact

An `AcquisitionArtifact` holds `records`, `steps` (one `StepResult` each),
`edges`, `groups`, `outcome`, `loss`, and the `manifest_id` and `as_of` it ran
under. `runner.run_scheduled` returns it beside the work ledger (a
`ledger.WorkLedgerEvent` tuple); `runner.run_acquisition` returns the artifact
alone.

A `StepResult` names its `step_id`, `adapter_id` and `route_id` (the route its
first page answered on; every record and every ledger operation carries the
exact route it came from), what the step spent and produced — `pages`,
`records_received`, `records_kept` — its `outcome`, `loss` and `warnings`, and
the step's own `kind` and `query`. An artifact carries steps and never the
manifest, so `kind` and `query` are the only place a reader learns what a step
was; `coverage.review_artifact` joins each record to its step through
`step_id` to decide whether a read deepened anything. An empty `kind` says the
result was assembled by hand rather than run.

`AcquisitionRecord` fields, by family:

| family | fields |
| --- | --- |
| identity | `record_id`, `artifact_id`, `manifest_id`, `step_id`, `adapter_id`, `adapter_version` |
| platform relation | `platform`, `native_identity_namespace`, `group_scope`, `representation_kind`, `canonical_content_kind`, `native_item_id`, `native_parent_id`, `canonical_locator`, `normalized_locator`, `author`, `community` |
| content | `title`, `body`, `exact_content_hash`, `attributes` |
| time | `published_at`, `observed_at`, `time_confidence`, `usable_basis_time` |
| engagement | `engagement`: a tuple of `EngagementSnapshot(metric_name, value, observed_at)` |
| page/order | `page_index`, `list_index`, `native_position` |
| access/provenance | `route_id`, `access_class`, `operator_identity`, `discovery_locator` |
| outcome/loss | `outcome`, `loss` |

Closed enums in `super_research.schema`: `STEP_KINDS`, `OUTCOMES` (`ok`,
`empty`, `partial`, `failed`, `refused`, ordered by severity for
`reduce_outcomes`), `ACCESS_CLASSES`, `REPRESENTATION_KINDS` (`index`,
`native`, `page`, `feed`, `transcript`), `TIME_CONFIDENCES`,
`PROVENANCE_EDGE_KINDS`, `GROUP_KEY_KINDS`. `canonical_content_kind` is open:
an adapter states the kind its origin reported.

**`engagement` admits only exact native integers.** A bool, a float, a
negative, or a value past `2^63-1` raises `NormalizeError` rather than being
coerced. A metric name is never inferred, aliased, summed, or compared across
platforms.

**`attributes` carries named non-integer facts `engagement` cannot**: exact
strings only, under the route's own names, repeating in the route's own order
where the route repeated them. A list flattened into one value or a number
stringified into it is refused by `normalize.named_attributes`.

**Time confidence.** `normalize.time_confidence_for` returns `unknown` with no
`published_at`, `reported` for a `K3` record, and `authoritative` otherwise: a
third-party archive reports the platform's time and is not the platform
speaking. `usable_basis_time` is `published_at`.

**Grouping never merges a hit into its target.** `strong_identity` is exactly
`(native_identity_namespace, native_item_id, canonical_content_kind)` and
requires all three. Without it a record falls to the five-field weak key
`(group_scope, representation_kind, normalized_locator,
canonical_content_kind, exact_content_hash)`, which requires every component;
a record with neither stands alone. `representation_kind` partitions every key
ahead of strong identity, so a search hit can never merge into the target it
discovered. That pair is a `discovery_hydration` edge instead, tied by the
locator the caller froze and matched exactly; its source is any discovery
record — one no hydration produced, from an index, a feed, or a native search
alike — whose normalized locator the hydration froze.

## Access ladder

Five classes plus `offline`, in preference order. No class takes a
user-supplied credential.

| class | meaning |
| --- | --- |
| `K0` | documented keyless official endpoint |
| `K1` | official endpoint under a client credential the vendor ships publicly |
| `K2` | structured data embedded in a public HTML page |
| `K3` | independent third-party archive of platform data, labelled with its operator identity |
| `K4` | web index for discovery, platform surface for hydration; a hit and its hydrated target are linked, never merged |
| `offline` | the `fake` fixture adapter; never live evidence |

A `K1` credential is a route constant attached at send time and never a
manifest or artifact field; the answering address is stripped of a
query-placed one before any caller sees it. A guest token is minted once per
process by the governor, as one paced read of its own; a failed activation is
remembered, and every read that needed its token is refused `auth_required`
rather than sent unauthorized.

## Adapter roster

Twenty-seven adapters, twenty-six live plus `fake`, over fifty-four route
surfaces; `x_guest`'s activation is spent rather than read, so it carries a
budget and never a record. Read back off `dispatch.surface_descriptors`.

| adapter | class | route surfaces | what ships |
| --- | --- | --- | --- |
| `web_search` | `K4` | `ddg_html`, `bing_rss`, `bing_news_rss`, `google_news_rss` | four web indexes as parallel planned routes: DDG HTML title/locator/snippet, and Bing's web and news RSS and Google News RSS, each with a publication time |
| `public_page` | `K0` | `public_page_article`, `public_page_control` | one selected static document: body, hash, links, content type, requested and final address |
| `open_page` | `K0` | `web_page_open` | any https document on a host no other route declares: title, prose, `ld+json` and `og:` metadata, publication time, content type, requested and final address |
| `reddit_archive` | `K3` | `arctic_shift_posts_ids`, `arctic_shift_posts_search` | Arctic Shift scoped, windowed post search and hydration by submission id: title, author, subreddit, permalink, created time, `score`, `num_comments` |
| `reddit_feed` | `K0` | `reddit_feed`, `reddit_search_feed` | subreddit RSS and global keyword search: title, locator, author, updated. No engagement |
| `reddit_shreddit` | `K2` | `reddit_shreddit_listing`, `reddit_shreddit_search`, `reddit_shreddit_subreddit_search`, `reddit_shreddit_comments` | the partials Reddit's own web client loads: a subreddit listing and a global and per-subreddit search, each with `score` and `comment-count`, and a post's comment page with per-comment `score`, depth and parent |
| `x_syndication` | `K2` | `x_syndication_timeline` | one handle's timeline from the page's own `__NEXT_DATA__`, with the platform's four counts |
| `x_xcancel` | `K3` | `xcancel_search`, `xcancel_status` | public Nitter HTML search and selected status hydration with per-record archive provenance; a browser challenge is a typed refusal, never performed |
| `x_fxtwitter` | `K3` | `fxtwitter_api` | an independent operator reading X: search by relevance or recency, a handle's statuses, a profile, and a conversation, each with the platform's own counts |
| `bluesky` | `K0` | `bluesky_search_posts`, `bluesky_author_feed` | the public AppView: post search with `since`/`until`, and one actor's feed, each with a post's four counts |
| `x_guest` | `K1` | `x_guest_activate`, `x_guest_graphql` | `TweetResultByRestId`, `UserByScreenName`, `UserTweets` on a guest token the process's first read mints as one extra paced call; the ledger bills that activation only when it refuses |
| `linkedin_public` | `K2` | `linkedin_public_profile` | `/in/<slug>` `ld+json` Person: name, description, `jobTitle`, `addressLocality`, `worksFor`, `alumniOf` |
| `linkedin_jobs` | `K0` | `linkedin_jobs_guest_search` | `jobs-guest` search: URN id, title, company, posted date |
| `youtube_innertube` | `K1` | `youtube_innertube`, `youtube_timedtext` | `search` result pages, `next` comment threads, `player` video metadata, and `transcript` — the caption track the player named, read as cues off the timed-text route. A `next` record's attributes come under the names of whichever thread shape answered (`voteCount`/`publishedTimeText`, or `likeCountNotliked`/`publishedTime`); nothing renames one into the other |
| `instagram_public` | `K1` | `instagram_web_profile` | `web_profile_info`: biography, follower count, recent posts with like and comment counts |
| `hacker_news` | `K0` | `hn_algolia_search`, `hn_firebase_item`, `hn_algolia_item` | Algolia search for stories and comments, Firebase v0 item and `kids` traversal, and one Algolia call returning a story's whole comment tree. Search asks `typoTolerance=false` |
| `github_rest` | `K0` | `github_rest`, `github_search` | anonymous repositories, issues, releases, search |
| `rss_atom` | `K0` | `youtube_channel_feed`, `web_page_open` | supplied public HTTPS feed URL or YouTube channel ID: RSS 2.0/Atom title, prose, original link, publication and separate modification, feed provenance, enclosures and transcript links |
| `prediction_markets` | `K0` | `polymarket_gamma`, `kalshi_markets`, `manifold_markets` | Polymarket search, events and markets, Kalshi's open markets and events, Manifold search; prices and volumes ride as the exact decimal strings each API wrote |
| `stocktwits` | `K0` | `stocktwits_symbol_stream`, `stocktwits_symbol_search` | one ticker's message stream with `likes.total` and the poster's `Bullish`/`Bearish` label, and symbol lookup |
| `gdelt` | `K4` | `gdelt_doc` | GDELT DOC 2.0's global news index: article hits with `url`, `title`, `seendate` and `domain`, bounded at the origin by `startdatetime`/`enddatetime` |
| `stack_exchange` | `K0` | `stackexchange_search_advanced` | questions over a named site with `score`, `answer_count` and `view_count`, bounded at the origin by `fromdate`/`todate`, under a 300/day anonymous quota the answer reports |
| `wikimedia_pageviews` | `K0` | `wikimedia_pageviews_per_article` | one article's daily view counts over a date range spelled as two path segments; a step with no window is refused, never defaulted |
| `scholarly` | `K0` | `openalex_works`, `crossref_works`, `arxiv_query` | scholarly works from one of three origins: OpenAlex with `cited_by_count`, Crossref DOI-anchored with `is-referenced-by-count`, arXiv preprints as Atom; each bounds publication time at the origin |
| `tiktok_public` | `K2` | `tiktok_video_page`, `tiktok_profile_page` | a public page's own rehydration JSON, no script run: a video with `createTime`, its `statsV2` counts, author and hashtags, and a profile with its own counts and no recent-video list |
| `oembed` | `K0` | `youtube_oembed`, `vimeo_oembed`, `spotify_oembed`, `soundcloud_oembed`, `tiktok_oembed`, `x_publish_oembed` | one platform URL hydrated into the item's own author, title and thumbnail through the platform's documented oEmbed endpoint; no date and no counts, both typed |
| `fake` | `offline` | `fake_offline` | deterministic fixture pages, never live evidence |

`rss_atom` reads a supplied URL through the shared open-page transport and host
budget; YouTube channel-feed URLs retain their dedicated route. It does not
search feeds or infer archive pagination. Publication dates may be unknown;
`updated` never makes an entry newly published. See [feed inputs and coverage](selection-routes.md#feeds).

No keyless read-only route exists for Instagram comments and feeds beyond the
one profile surface, Threads, Pinterest, Facebook, Truth Social, TikTok
comments and search, or Reddit's `more-comments` continuation (a POST this
package does not admit): an answer over them files a declared gap rather than
implying coverage.

## Loss vocabulary

Loss is typed and additive: a code says what is missing or how the answer was
qualified, and an outcome says how the read ended. A record carrying a loss
code is not a failed read — a `youtube_innertube` player that withholds its
caption tracks still returns `ok` with the metadata it did get. A route that
fails does not fall back; `schema_drift` and `stale_identifier` exist so a
changed payload is a typed failure rather than an empty success.

| code | means |
| --- | --- |
| `third_party_archive` | an independent archive answered, not the platform; on every `K3` record |
| `stale_identifier` | a vendor identifier rotated (an X query id answers 404, a YouTube client version 400); the read was refused, not empty |
| `attestation_required` | the origin withheld a payload behind an attestation this package does not perform: a browser challenge, or a YouTube player withholding caption tracks |
| `network_intercepted` | the local network answered, not the origin |
| `unreachable` | the read raised instead of answering: the channel carried nothing (name, connection, TLS, timeout); the transport declined to send it (not https, a write-capable method, an undeclared route or credential, an open-page address its policy refuses); a body declared gzip that is not gzip, cut short or corrupt; a guest activation that never answered; or a plan's own bound (request cap, elapsed time, `as_of` passed). The error text rides as the step's warning and the ledger bills no call |
| `cache_hit` | this run's own memory answered |
| `archive_lag` | vocabulary only, never emitted: one archive read cannot measure platform-wide lag |
| `scope_required` | `reddit_archive` search requires a subreddit or author scope; refused before I/O |
| `discovery_not_recorded` | this run discovered, and the discovery record this hydration names is not in this artifact. A hydration-only dispatch established no lineage and says nothing |
| `auth_required` | the origin refused over who is asking, or a guest activation failed and every read that needed its token was refused rather than sent unauthorized |
| `no_route` | the core declares no such adapter |
| `rate_limited` | the origin asked for fewer requests (HTTP 429; `reddit_archive`'s 422) |
| `schema_drift` | the payload arrived in a shape this parser does not know, so an empty result would have been a lie |
| `field_omitted` | the answer carried, and one declared field of the roster row was not in it |
| `malformed_json` | the body did not parse as the JSON the route declares |
| `http_status` | the origin answered with a status the route does not read as an answer |
| `withheld` | a YouTube player declined the payload with a playability status this package cannot class further |
| `engagement_unavailable` | this surface publishes no counts (`reddit_feed`, `web_search`, `oembed`, `gdelt`), so a zero would be a number nobody reported |
| `date_precision_only` | the origin gave a date and no time |
| `unselected_target` | this route does not serve the selection it was asked for: an open-page address its policy refuses, a Shreddit target its grammar does not name, a TikTok argument naming no address, a Wikimedia hydration with no article or no `window_start`, an oEmbed target naming no provider |
| `native_identity_unknown` | the row carries no platform-native id; on every index hit |
| `unknown_publication_time` | the row carries no publication time; on every DuckDuckGo hit and every oEmbed record |
| `target_not_hydrated` | this hit was discovered and nothing in this artifact hydrated it; on every index hit |
| `recall_window_partial` | a cap truncated the step, or it stopped while the origin was still offering: the set is a window, not the whole |
| `window_not_honored` | the step carried a window and called an operation `runner.WINDOW_REACH` declares unable to bound time at its origin |
| `window_capability_unmeasured` | the step carried a window and called an operation declared but never measured |

## Ordering contract

Five named views, in `ordering.ORDERING_CONTRACT`: `newest`,
`cross_source_chronology`, `native_top`, `most_commented`, `most_replied`.
Anything else raises `OrderingError`. Every view but chronology orders inside a
single `(platform, canonical_content_kind)` family and refuses a mixed set.

No wall clock participates. Every string is compared as unsigned UTF-8 bytes
over its NFC form; a missing value sorts after every present one, and
`record_id` byte order is the terminal tie.

- `newest`: `usable_basis_time` descending, then native item id, then record id.
- `cross_source_chronology`: `usable_basis_time` descending, then platform,
  identity namespace, content kind, record id.
- `native_top`: the origin's own ordinal ascending, then native item id, then
  record id.
- `most_commented` and `most_replied`: the eligible engagement snapshot
  descending, then `usable_basis_time`, then native item id, then record id.

An eligible snapshot is the greatest observation at or before `as_of`, ties
broken by the snapshot's earliest declared position and never by value. An
observation after `as_of` is not eligible, so the replay answers the same way
whenever it runs. The two counted orders read the exact metric the surface
declares in `comment_count_metric` or `reply_count_metric`; a surface
declaring neither has no eligible metric. A counted view over a set in which
nothing counts raises `OrderingError` naming why, rather than answering with
chronology under a counted name; `ordering.observation_horizon(records)` is
the smallest `as_of` that admits every snapshot.

## Running a manifest

The routine path is the [bounded plan](acquisition.md). To run one manifest
directly, write it to a file and run this from a lane-private directory with
the scripts directory on `PYTHONPATH`:

```
python -c "import dataclasses, json, sys
from super_research import runner, schema
manifest = schema.parse_manifest(json.load(open(sys.argv[1], encoding='utf-8')))
print(manifest.manifest_id, manifest.as_of, len(manifest.steps), 'steps')
artifact = runner.run_acquisition(manifest)
json.dump(dataclasses.asdict(artifact), open(sys.argv[2], 'w', encoding='utf-8'), indent=1)
print(artifact.outcome, artifact.loss, len(artifact.records), 'records')
" manifest.json artifact.json
```

Compare the printed id, horizon and step count to what was intended before any
transport call. Read each `StepResult`'s `outcome`, `loss` and `warnings`
before any record. Set `window_start`/`window_end` on every step whose question
has a window. Order afterwards with `runner.order_records` at an `as_of` at or
after the run's own reads. `coverage.plan_depth` builds the hydration steps
that deepen discovery records; `coverage.review_manifest` and
`coverage.review_artifact` say what a run is about to miss and what it missed.

## Pacing and cache

Every route declares its ceiling (`min_interval_ms`, `burst`, `cooldown_ms`)
and `pacing.RateGovernor` waits it out per route, serializing reads per origin
host; a `Retry-After` or `X-RateLimit-Reset` the origin states lengthens the
cooldown and never shortens it. `transport.urlopen_read` reads at most
`MAX_RESPONSE_BYTES` (8 MiB), https only, on the route's admitted methods.

`cache.RunCache` is keyed by `(route_id, canonical_request)`, holds at most
`MAX_ENTRIES=32` bodies of at most `MAX_ENTRY_BYTES=1 MiB`, runs on a monotonic
clock, and dies with the run — `close()` makes a later run's reach for it an
error rather than a quiet hit. Their product, 32 MiB, is what a run's cache can
cost however long the run goes on. Per-route TTLs are declared in
`cache.ROUTE_TTL_SECONDS`; a cache hit costs the route's budget nothing and
carries `cache_hit` on the page and every record.
