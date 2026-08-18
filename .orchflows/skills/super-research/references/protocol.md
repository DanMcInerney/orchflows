# super-research protocol

`SKILL.md` is the contract. This is the detail behind it: the manifest a caller
writes, the record it gets back, the ladder every route is classed on, the codes
a partial answer carries, and the orders a set may be put in. Names here are the
package's own — a term in `code` is a name the source spells exactly that way.

What every ceiling, field list and route constant below traces to is in
[evidence.md](evidence.md), which is also where the liveness sweeps and the
captive-portal caveat are.

## Manifest grammar

`schema.parse_manifest` validates totally, before any transport call, and raises
`ManifestError` on anything it cannot accept. An unknown key at any level is
rejected rather than ignored.

Manifest keys are exactly `schema_version`, `manifest_id`, `mode`, `as_of`,
`steps`.

- `schema_version` must equal `2`. There is no other manifest schema.
- `manifest_id` and `as_of` are nonempty strings.
- `mode` is `staged` or `fused`. The artifact is the same either way — records
  and steps are assembled in declared order — and the mode reaches the wall
  clock and the ledger's placement. `staged` runs its steps one at a time in
  declared order, so a caller can select hits between one step's output and
  the next step's input. `fused` runs each adapter's steps as one **lane**, in
  declared order within the lane, and overlaps the lanes on a pool of at most
  `runner.MAX_CONCURRENT_LANES` (8): a manifest naming Reddit, Hacker News,
  YouTube and Bing runs its four lanes at once. That is safe because a step's
  inputs are frozen in the manifest — a hydration reads `selected_hits` the
  caller froze, never what another lane produced — and because the governor
  serializes reads **per origin host** whatever the lanes do (`pacing`
  §"Serialized per origin"): an origin never sees two of this package's reads
  in flight, and pacing stays per route. `run_scheduled(..., lanes=1)` runs a
  fused manifest serially. The ledger's placement model is `ledger.schedule_of`'s
  and now names what runs.
- `steps` is a nonempty sequence of steps with unique `step_id`s; a
  `prior_step_id` must name a step in the same manifest.

Step keys are exactly `step_id`, `kind`, `adapter_id`, `query`, `prior_step_id`,
`selected_hits`, `max_items`, `window_start`, `window_end`.

- `kind` is `discovery` or `hydration`. A discovery step forbids `selected_hits`
  and authorizes one call, plus a continuation of it per page that offers a
  cursor, bounded below. A hydration step requires them and authorizes one call
  per hit and nothing further, which is what makes each hydration record's
  provenance exact rather than inferred: a page read off a cursor was authorized
  by nobody.
- Each hit is exactly `{discovery_locator, target_id}`, both nonempty.
  `discovery_locator` is the normalized locator the caller saw in the discovery
  step's output; it is the only thing that ties a hydration record back to its
  discovery record, and nothing is matched by similarity.
- `max_items` is a hard positive integer cap. It is required — there is no
  default and no unbounded step. On a discovery step it bounds the whole step,
  and the core owns stop: no further call is made once the cap is met. On a
  hydration step it bounds **each authorized call** — every selected hit was
  authorized by name and every one is called, and a first hit that answers
  richly cannot starve the ones the caller also selected; the step is bounded
  by hits × `max_items`. A step that truncated either way emits
  `recall_window_partial`. **The core pages.** A discovery step reads the page
  its `cursor_out` names, to `runner.MAX_PAGES_PER_STEP` (5); a step that
  stopped while the origin still offered emits `recall_window_partial`. A
  discovery step whose cap is under the surface's declared `page_size` gets a
  warning saying so before the read: one call returns the page whatever the
  cap, and the rows past it are dropped at no saving.
- `window_start` and `window_end` are optional instants in the same spelling as
  `as_of`, either or both empty, `window_start` not after `window_end`. A record
  the origin dated outside the window is dropped by the core **before the cap
  counts it**, so the cap is spent in-window rather than on an origin's
  all-time-top ordering (X's syndication timeline is the measured case); a
  record with no publication time is kept, because dropping it would decide
  the unknown. The step's warning states how many were dropped; no loss code
  is attached, because the bound is the caller's own. Adapters whose origin
  takes a date bound send it in the origin's own terms as well (Arctic Shift
  `after`/`before`, HN Algolia `numericFilters`, Bluesky `since`/`until`, Google
  News `when:`), so the budget is spent server-side where it can be.

`as_of` must be spelled `YYYY-MM-DDTHH:MM:SSZ` and `parse_manifest` refuses any
other spelling, because `ordering.instant_seconds` returns nothing for one and an
`as_of` that does not parse silently stops bounding which engagement snapshots are
eligible — the replay is then no longer frozen. `schema.INSTANT_FORMAT` is the one
definition; `ordering` reads it from there. The same format governs every instant
the ordering reads, but only `as_of` is refused: a `published_at` carrying an
offset or a fractional second is an origin's own spelling and sorts as missing
rather than as a time.

## The record: `AcquisitionArtifact v2` field families

One `AcquisitionArtifact` holds `records`, `steps` (one `StepResult` each),
`edges`, `groups`, `outcome`, `loss`, and the `manifest_id`, `mode` and `as_of` it
was run under. Grouping never rewrites a record: two records describing one thing
are held side by side by a group's membership or by a provenance edge, and each
keeps its own body, time, route, and metric snapshots.

The retained families, with the fields this delivery actually carries on
`AcquisitionRecord`:

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
| audit | the artifact's `steps` and, from `runner.run_scheduled`, its `WorkLedgerEvent` tuple |

Closed enums, all in `schema.py`: `ACQUISITION_MODES`, `STEP_KINDS`, `OUTCOMES`
(`ok`, `empty`, `partial`, `failed`, `refused`, ordered by severity for
`reduce_outcomes`), `ACCESS_CLASSES`, `REPRESENTATION_KINDS` (`index`, `native`,
`page`, `feed`, `transcript`), `TIME_CONFIDENCES`, `PROVENANCE_EDGE_KINDS`,
`GROUP_KEY_KINDS`.

`canonical_content_kind` is not a closed enum: an adapter states the kind its
origin reported. Those shipping today are `web_hit`, `web_page`, `post`,
`profile`, `job_posting`, `feed_entry`, `video`, `comment`, `repository`, `issue`,
`release`, and Hacker News's own item types (`story`, `comment`, `poll`,
`pollopt`, `job`).

**`engagement` admits only exact native integers.** A bool, a float, a negative,
or a value past `2^63-1` raises `NormalizeError` rather than being coerced. A
metric name is never inferred, aliased, summed, or compared across platforms.

**`attributes` carries named non-integer facts `engagement` cannot.** It is a
defaulted `Tuple[Tuple[str, str], ...]` on `NativeRecord` and `AcquisitionRecord`:
exact strings only, under the route's own names, repeating in the route's own
order where the route repeated them. A list flattened into one value, or a number
stringified into it, would be a fact this package made rather than one a route
reported, so `normalize.named_attributes` refuses both. It is where a structured
public page's own vocabulary lands — `jobTitle`, `addressLocality`, `worksFor`,
`alumniOf` on a LinkedIn profile; `content_type`, `link`, `requested_url`,
`final_url` on a fetched page — for names where `title`, `body` and `community`
each already mean something else.

**Time confidence.** `normalize.time_confidence_for` returns `unknown` with no
`published_at`, `reported` for a `K3` record, and `authoritative` otherwise: a
third-party archive reports the platform's time and is not the platform speaking.
`usable_basis_time` is `published_at`.

**Grouping, and the rule that a hit is never its target.** `strong_identity` is
exactly `(native_identity_namespace, native_item_id, canonical_content_kind)` and
requires all three. Without it a record falls to the five-field weak key
`(group_scope, representation_kind, normalized_locator, canonical_content_kind,
exact_content_hash)`, which requires every component; a record with neither stands
alone. `representation_kind` partitions every grouping key ahead of strong
identity, so a search hit can never merge into the target it discovered even if
the two presented the same strong identity. That pair is a `discovery_hydration`
edge instead, tied by the locator the caller froze and matched exactly. The
edge's source is **any discovery record** — one no hydration produced, from an
index, a feed, or a native search alike — whose normalized locator the
hydration froze; until 2026-08-17 only an `index` record could be a source, so
a fused manifest discovering on a feed and hydrating what it found formed no
edge and typed every hydration `discovery_not_recorded`, which forced every
discovery→hydration pair to be staged as two dispatches.

## Access ladder

Six classes plus `offline`, ordered by **preference, not authority** — every class
but `K5` is uncredentialed.

| class | meaning |
| --- | --- |
| `K0` | documented keyless official endpoint |
| `K1` | official endpoint under a client credential the vendor ships publicly |
| `K2` | structured data embedded in a public HTML page |
| `K3` | independent third-party archive of platform data |
| `K4` | web index for discovery, platform surface for hydration |
| `K5` | user-supplied credential — an optional throughput upgrade, never a precondition |
| `offline` | the `fake` fixture adapter; never live evidence |

1. No first-release capability may depend on `K5`. Absence of a credential yields
   full capability at lower throughput, never a refusal.
2. A `K3` route is labelled with its operator identity and carries
   `third_party_archive` on **every record**, never on the page alone.
3. A `K4` discovery hit and its hydrated target are linked, never merged.

How each class is enforced — the credential's placement, the class check at
construction, and why no lawful `K5` shape exists — is in
[internals.md](internals.md) §"How the ladder is enforced".

## Adapter roster

Twenty adapters, nineteen live plus `fake`; thirty-six route surfaces, because
ten adapters reach more than one — `bluesky`, `x_guest` and `youtube_innertube`
among them, each pairing a second endpoint to its first. Thirty-five of the
thirty-six are read;
`x_guest`'s activation is spent rather than read, so it carries a budget and
never a record. Read back off `runner.surface_descriptors`.

| adapter | class | route surfaces | what ships |
| --- | --- | --- | --- |
| `web_search` | `K4` | `ddg_html`, `bing_rss`, `bing_news_rss`, `google_news_rss` | four web indexes as parallel planned routes, never fallbacks: DDG HTML title/locator/snippet, and Bing's web and news RSS and Google News RSS, each with a publication time and a paging or windowing term of its own |
| `public_page` | `K0` | `public_page_article`, `public_page_control` | one selected static document: body, hash, links, content type, requested and final address |
| `open_page` | `K0` | `web_page_open` | any https document on a host no other route declares: title, prose, `ld+json` and `og:` metadata, publication time, content type, requested and final address. The one route whose host is the caller's |
| `reddit_archive` | `K3` | `arctic_shift_posts_ids` | Arctic Shift hydration by submission id: title, author, subreddit, permalink, created time, `score`, `num_comments` |
| `reddit_feed` | `K0` | `reddit_feed` | subreddit RSS freshness probe: title, locator, author, updated. No engagement |
| `reddit_shreddit` | `K2` | `reddit_shreddit_listing`, `reddit_shreddit_search`, `reddit_shreddit_subreddit_search`, `reddit_shreddit_comments` | the partials Reddit's own web client loads: a subreddit listing and a global and per-subreddit search, each with `score` and `comment-count`, and a post's comment page with per-comment `score`, depth and parent. Reddit search and Reddit comments, which no other route in this roster reaches |
| `x_syndication` | `K2` | `x_syndication_timeline` | one handle's timeline from the page's own `__NEXT_DATA__`, with the platform's four counts |
| `x_fxtwitter` | `K3` | `fxtwitter_api` | an independent operator reading X: search by relevance or recency, a handle's statuses, a profile, and a conversation, each with the platform's own counts. The one keyless X **search** in the roster — `x_search` stays deferred and this is not it speaking for the platform, so every record carries `third_party_archive` |
| `bluesky` | `K0` | `bluesky_search_posts`, `bluesky_author_feed` | the public AppView: post search with `since`/`until`, and one actor's feed, each with the four counts a post carries. Measured 2026-08-17: the search method answered 403 from the CDN in front of it on this host while the feed answered 200, so the smoke names the feed |
| `x_guest` | `K1` | `x_guest_activate`, `x_guest_graphql` | a guest-token activation, then `TweetResultByRestId`, `UserByScreenName`, `UserTweets` on the token it minted. One read costs two origin calls; both are paced, and the ledger bills the read alone — the activation is in the governor's log |
| `linkedin_public` | `K2` | `linkedin_public_profile` | `/in/<slug>` `ld+json` Person: name, description, `jobTitle`, `addressLocality`, `worksFor`, `alumniOf` |
| `linkedin_jobs` | `K0` | `linkedin_jobs_guest_search` | `jobs-guest` search: URN id, title, company, posted date |
| `youtube_innertube` | `K1` | `youtube_innertube`, `youtube_timedtext` | four operations a caller names one of: `search` result pages, `next` comment threads, `player` video metadata, and `transcript` — the caption track the player itself named, read as cues off the timed-text route beside it. Measured 2026-08-17: 449 cues and 16,957 characters from one video. A `next` record's attributes come under the names of whichever thread shape answered, and both shapes are in the wild: the pre-2026-08 `comment.commentRenderer` shape names `voteCount` and `publishedTimeText`, while the `commentViewModel` shape every read today returns names `likeCountNotliked` and `publishedTime`. Read the pair a record actually carries and expect either — nothing renames one into the other, because a name this package made would not be a name an origin reported |
| `instagram_public` | `K1` | `instagram_web_profile` | `web_profile_info`: biography, follower count, recent posts with like and comment counts |
| `hacker_news` | `K0` | `hn_algolia_search`, `hn_firebase_item`, `hn_algolia_item` | Algolia search for stories and comments, Firebase v0 item and `kids` traversal, and one Algolia call that returns a story's whole comment tree — 259 nodes in one read, measured 2026-08-17. Search asks `typoTolerance=false`, because the index reaches `space` from `SpaceX` otherwise |
| `github_rest` | `K0` | `github_rest`, `github_search` | anonymous repositories, issues, releases, search |
| `rss_atom` | `K0` | `youtube_channel_feed` | one generic RSS 2.0 and Atom parser: identity, dates, enclosures, transcript links |
| `prediction_markets` | `K0` | `polymarket_gamma`, `kalshi_markets`, `manifold_markets` | the odds on a question with a date: Polymarket search, events and markets, Kalshi's open markets and events, Manifold search. Prices and volumes are decimals and ride as the exact strings each API wrote |
| `stocktwits` | `K0` | `stocktwits_symbol_stream`, `stocktwits_symbol_search` | one ticker's message stream with `likes.total` and the poster's own `Bullish`/`Bearish` label, and symbol lookup. The roster's one finance-native surface |
| `fake` | `offline` | `fake_offline` | deterministic fixture pages. Never live evidence, and the one adapter with no smoke |

`rss_atom` is a generic feed parser bound to one declared route. A second feed is
a second route constant in `routes.py`, not a caller-supplied address; the
adapter never names a host.

Deferred, each with a reopen condition rather than a silent drop:
`youtube_captions` — **reopened and no longer blocked**: the `ANDROID` InnerTube
client answered `OK` with `captionTracks` on 2026-08-17 where `WEB` still
answers `UNPLAYABLE`, and `evidence.md` §"The route sweep of 2026-08-17"
records it, so the deferral now waits on the adapter work rather than on the
attestation; `x_search` (the current `SearchTimeline` query id is unrecovered
behind an ESM import map) with `K4` as the interim route, and FxTwitter as a
`K3` operator that does serve a search; Arctic Shift's `posts/search`,
`comments/search` and `comments/tree`, all three measured answering 200 the
same day, until an adapter reads them — Reddit search and comments themselves
are no longer waiting on that, because `reddit_shreddit` reaches both;
Reddit's `more-comments` continuation, because it asks for a POST and this
package admits two, both named; `tiktok_public`, unverified because this
network answered 503 with a login portal and `evidence.md` §"The
captive-portal caveat" forbids reading that as platform behaviour; Bluesky's
`searchPosts`, which answered 403 from the CDN in front of the public AppView
on this host while its sibling methods answered 200; and `reddit_oauth` and
`youtube_data_api` as `K5` throughput upgrades.

## Failure and loss vocabulary

Loss is typed and additive: a code says what is missing or how the answer was
qualified, and an outcome says how the read ended. They are read together. A
record carrying a loss code is not a failed read — `youtube_innertube` returns
`ok` with `attestation_required` when a player withholds caption tracks and still
carries the metadata it did get.

**named by** is every module whose executable code spells that code, to attach
it or to read it. Every table below is read back off this file by
`test_dependency_boundary.LossVocabularyIsReadOffTheSourceTest`, so a cell that
stops being true is a red test rather than a sentence nobody re-read.

The eight codes this delivery adds to the retained vocabulary:

| code | means | named by |
| --- | --- | --- |
| `third_party_archive` | an independent archive answered, not the platform | `reddit_archive`, `x_fxtwitter` |
| `stale_identifier` | a vendor identifier rotated; the read was refused, not empty | `x_guest` (404), `youtube_innertube` (400) |
| `attestation_required` | the origin withheld a payload behind an attestation this package does not perform | `youtube_innertube`, for the two playability statuses evidence.md §"Route measurements of 2026-08-10" records and for a withheld caption list; `cli`, which reads it |
| `network_intercepted` | the local network answered, not the origin | `transport`, `adapters`, `smoke` |
| `unreachable` | the read raised instead of answering: nothing took it — not the origin, and not an appliance in front of it — or the transport itself declined to send it (an address that is not https, a write-capable method, a route or credential it does not declare). The exception's own text rides as the step's warning and says which; the ledger bills no call for it | `runner`, which ends the step on it; `smoke` and `cli`, which read it |
| `cache_hit` | this run's own memory answered | `adapters`, `runner` |
| `archive_lag` | an archive's coverage trails the platform | nothing: **absent from the source entirely** |
| `scope_required` | an archive query needs a scope it was not given | nothing: **absent from the source entirely** |

`archive_lag` and `scope_required` are named in this table and nowhere else in the
delivery: not emitted, and not declared either. The one Arctic Shift route
delivered is `posts/ids`, which is hydration by exact id and takes no scope;
`posts/search`, `comments/search` and `comments` by `link_id` — where the spec's
grammar rule that `title=` requires `subreddit` or `author` lives, and where a lag
window would be observable — are not shipped. The two codes are named here so a
later route adds a code the vocabulary already has, and so nobody reads their
absence from the source as the vocabulary being smaller than the spec says.

Added after those eight, and the only code here derived across the record set
rather than read off a page:

| code | means | named by |
| --- | --- | --- |
| `discovery_not_recorded` | this run discovered, and the discovery record this hydration names is not in this artifact | `normalize` |

The clause before the comma is half the claim, and dropping it would make the
code lie in the ordinary case. A `staged` hydration runs as its own dispatch,
against a selection the caller froze from an artifact this one has never seen —
so an artifact holding hydrations and no discovery at all has established no
lineage and missed nothing, and says nothing. Only a run that discovered can
report that its own discovery does not account for what it hydrated. The two
cases are indistinguishable from a step list, which is why the rule is written
against the records: a record with no `discovery_locator` is a discovery record,
because the schema requires a nonempty one on every selected hit.

A discovery step that returned no rows at all reads, from the records alone,
exactly like a hydration-only dispatch, so that run stays silent too. That is a
gap this code does not cover rather than one it hides: the step's own failure is
already typed on its `StepResult`.

`discovery_not_recorded` is the mirror of `target_not_hydrated` below, which
states the same relation in the other direction — a hit nobody hydrated. The
pair is deliberate. Neither is evidence about the platform: they describe what
one artifact does and does not hold.

The retained codes, what each one means, and every module that spells one:

| code | means | named by |
| --- | --- | --- |
| `auth_required` | the origin refused over who is asking, or the route needs a credential this package does not supply | `bluesky`, `router`, `x_guest`, `linkedin_public`, `instagram_public`, `youtube_innertube`, `cli` — the router for a K5 route, the four adapters for an origin's own refusal, `cli` reading it |
| `no_route` | the core declares no such adapter or route | `router`, `runner`, for an adapter or route the core does not declare |
| `rate_limited` | the origin asked for fewer requests | `adapters`, on HTTP 429 |
| `schema_drift` | the payload arrived in a shape this parser does not know, so an empty result would have been a lie | `bluesky`, `github_rest`, `hacker_news`, `instagram_public`, `linkedin_jobs`, `linkedin_public`, `prediction_markets`, `reddit_archive`, `reddit_feed`, `reddit_shreddit`, `rss_atom`, `stocktwits`, `web_search`, `x_guest`, `x_syndication`, `youtube_innertube`, `x_fxtwitter` |
| `field_omitted` | the answer carried, and one declared field of the roster row was not in it | `bluesky`, `github_rest`, `hacker_news`, `instagram_public`, `linkedin_jobs`, `linkedin_public`, `open_page`, `prediction_markets`, `reddit_archive`, `reddit_feed`, `reddit_shreddit`, `rss_atom`, `stocktwits`, `web_search`, `x_syndication`, `youtube_innertube`, `x_fxtwitter` |
| `malformed_json` | the body did not parse as the JSON the route declares | `bluesky`, `fake`, `github_rest`, `hacker_news`, `instagram_public`, `linkedin_public`, `prediction_markets`, `reddit_archive`, `stocktwits`, `x_guest`, `x_syndication`, `youtube_innertube`, `x_fxtwitter` |
| `http_status` | the origin answered with a status the route does not read as an answer | `bluesky`, `github_rest`, `hacker_news`, `instagram_public`, `linkedin_jobs`, `linkedin_public`, `open_page`, `prediction_markets`, `public_page`, `reddit_archive`, `reddit_feed`, `reddit_shreddit`, `rss_atom`, `stocktwits`, `web_search`, `x_guest`, `x_syndication`, `youtube_innertube`, `x_fxtwitter` — seventeen, which is every adapter that reads an origin |
| `withheld` | the origin declined the payload and said nothing this package can class further | `youtube_innertube`, for a playability refusal the evidence did not record |
| `engagement_unavailable` | this surface publishes no counts at all, so a zero would be a number nobody reported | `reddit_feed`, `web_search` |
| `date_precision_only` | the origin gave a date and no time, so the instant is the date's | `linkedin_jobs`, `open_page`, `youtube_innertube` |
| `unselected_target` | this route does not serve the selection it was asked for | `open_page`, for an address its policy refuses; `public_page`, for a selection this route does not serve; `reddit_shreddit`, for a target its grammar does not name |
| `native_identity_unknown` | the row carries no platform-native id, so it can never group by strong identity | `web_search`, standing on every index hit |
| `unknown_publication_time` | the row carries no publication time, so it sorts as missing | `web_search`, standing on every index hit |
| `target_not_hydrated` | this hit was discovered and nothing in this artifact hydrated it | `web_search`, standing on every index hit |
| `recall_window_partial` | the step stopped while the origin was still offering, so the set is a window and not the whole | `runner`, when a cap truncated; `coverage`, which reads it |

Five of the names above are readers rather than emitters: `runner.reached_origin`
reads `cache_hit`, `smoke.channel_of` reads `network_intercepted` and
`unreachable`, `cli.target_may_be_the_problem` reads `auth_required` and
`attestation_required`, and `coverage.review_artifact` reads
`recall_window_partial` to tell a caller its own set is a window rather than
the whole. Everywhere else, naming a code is attaching it.

A route that fails does not fall back. `schema_drift` and `stale_identifier` exist
so that a changed payload is a typed failure rather than an empty success, which
is the one outcome a caller cannot tell from "there is nothing there".

## Ordering contract

Five named views, in `ordering.ORDERING_CONTRACT`: `newest`,
`cross_source_chronology`, `native_top`, `most_commented`, `most_replied`. Ask for
anything else and `order_records` raises `OrderingError`.

Four of the five — every one but chronology — order inside a single
`(platform, canonical_content_kind)` family and **refuse a mixed set** rather than
ordering a Reddit post against a web hit. Chronology crosses source roles on
purpose.

No wall clock participates. Every string is compared as unsigned UTF-8 bytes over
its NFC form, so an order never depends on a locale or on how a string was
composed. A missing value sorts after every present one, and `record_id` byte
order is the terminal tie everywhere.

- `newest`: `usable_basis_time` descending, then native item id, then record id.
- `cross_source_chronology`: `usable_basis_time` descending, then platform,
  identity namespace, content kind, record id.
- `native_top`: the origin's own ordinal ascending, then native item id, then
  record id.
- `most_commented` and `most_replied`: the eligible engagement snapshot
  descending, then `usable_basis_time`, then native item id, then record id.

An eligible snapshot is the **greatest observation at or before the manifest's
`as_of`**, ties broken by the snapshot's earliest declared position and never by
value — picking the larger of two simultaneous readings would let a comparator
improve its own inputs. Position, because it is the only stable thing a snapshot
has: `EngagementSnapshot` carries no id and a record's snapshots are an
immutable tuple. It is compared as a number and never as a derived
`record#e<position>` string, which sorts `#e10` below `#e2` and would break the
tie by how the number was spelled. An observation after `as_of` is not eligible
at all, so the replay answers the same way whenever it runs.

The two counted orders read the exact metric name the surface declares in
`comment_count_metric` or `reply_count_metric`. An adapter declaring neither has
no eligible metric, which is a stated absence rather than a zero nobody reported.

**A counted view over a set in which nothing counts is refused.** When no
record in the set has an eligible snapshot — the surfaces declare no metric,
or every observation is after `as_of` — `order_records` raises
`OrderingError` naming which, rather than answering with chronology under a
counted name (the silent degradation the 2026-08-17 bakeoff measured: a
frozen `as_of` at noon over records observed at half past returned `newest`
under `most_commented` and nothing said so). The repair costs no
re-acquisition: `ordering.observation_horizon(records)` is the latest moment
any engagement in the set was observed, and ordering at or after it — as a
second, labelled horizon — admits every snapshot. A frozen `as_of` should
therefore be at or after the run's own reads; a set in which some records
count still orders, with the uncounted after every counted one.

## Relevance

`relevance` is the auditable counterpart to a hidden relevance floor. One
query compiles once (`compile_query`: quoted segments are phrases, the rest
are stems with stopwords dropped); every record is scored against it
(`match`, `rank`) with the terms and phrases that earned the score and the
field each was found in; `partition(records, query, floor)` returns the kept
and the dropped **both**, and `audit_lines` renders the drops for a report. A
term matches whole tokens only, under a stemmer that strips plurals and
inflections and nothing else, so `valuation` never matches `e-valuation` and
`shares` meets `share` by name. A score never reads engagement, a parent's
counts, or another platform: those are the calling lane's decisions, made in
the open. Nothing here drops a record on its own.
