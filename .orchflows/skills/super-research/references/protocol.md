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
- `mode` is `staged` or `fused`. Steps run in declared order either way and the
  artifact is the same; `fused` runs discovery and its hydration in one
  invocation, `staged` returns after each step so the caller selects hits
  between them. Nothing runs concurrently; the ledger's placement model is
  `ledger.schedule_of`'s.
- `steps` is a nonempty sequence of steps with unique `step_id`s; a
  `prior_step_id` must name a step in the same manifest.

Step keys are exactly `step_id`, `kind`, `adapter_id`, `query`, `prior_step_id`,
`selected_hits`, `max_items`.

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
  default and no unbounded step. The core owns stop: no further call is made once
  the cap is met, and a step that truncated emits `recall_window_partial`.
  **The core pages.** A discovery step reads the page its `cursor_out` names, to
  `runner.MAX_PAGES_PER_STEP` (5); a step that stopped while the origin still
  offered emits `recall_window_partial`.

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
edge instead, tied by the locator the caller froze and matched exactly.

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

Fourteen adapters, thirteen live plus `fake`; eighteen route surfaces, because
four adapters reach more than one. Seventeen of the eighteen are read; `x_guest`'s
activation is spent rather than read, so it carries a budget and never a record.
Read back off `runner.surface_descriptors`.

| adapter | class | route surfaces | what ships |
| --- | --- | --- | --- |
| `web_search` | `K4` | `ddg_html` | DDG HTML discovery: title, locator, snippet |
| `public_page` | `K0` | `public_page_article`, `public_page_control` | one selected static document: body, hash, links, content type, requested and final address |
| `reddit_archive` | `K3` | `arctic_shift_posts_ids` | Arctic Shift hydration by submission id: title, author, subreddit, permalink, created time, `score`, `num_comments` |
| `reddit_feed` | `K0` | `reddit_feed` | subreddit RSS freshness probe: title, locator, author, updated. No engagement |
| `x_syndication` | `K2` | `x_syndication_timeline` | one handle's timeline from the page's own `__NEXT_DATA__`, with the platform's four counts |
| `x_guest` | `K1` | `x_guest_activate`, `x_guest_graphql` | a guest-token activation, then `TweetResultByRestId`, `UserByScreenName`, `UserTweets` on the token it minted. One read costs two origin calls; both are paced, and the ledger bills the read alone — the activation is in the governor's log |
| `linkedin_public` | `K2` | `linkedin_public_profile` | `/in/<slug>` `ld+json` Person: name, description, `jobTitle`, `addressLocality`, `worksFor`, `alumniOf` |
| `linkedin_jobs` | `K0` | `linkedin_jobs_guest_search` | `jobs-guest` search: URN id, title, company, posted date |
| `youtube_innertube` | `K1` | `youtube_innertube` | `search`, `next` comment threads, `player` metadata. No captions |
| `instagram_public` | `K1` | `instagram_web_profile` | `web_profile_info`: biography, follower count, recent posts with like and comment counts |
| `hacker_news` | `K0` | `hn_algolia_search`, `hn_firebase_item` | Algolia search for stories and comments, plus Firebase v0 item and `kids` traversal |
| `github_rest` | `K0` | `github_rest`, `github_search` | anonymous repositories, issues, releases, search |
| `rss_atom` | `K0` | `youtube_channel_feed` | one generic RSS 2.0 and Atom parser: identity, dates, enclosures, transcript links |
| `fake` | `offline` | `fake_offline` | deterministic fixture pages. Never live evidence, and the one adapter with no smoke |

`rss_atom` is a generic feed parser bound to one declared route. A second feed is
a second route constant in `routes.py`, not a caller-supplied address; the
adapter never names a host.

Deferred, each with a reopen condition rather than a silent drop: `youtube_captions`
(PoToken attestation; `captionTracks` was empty on five clients across three
videos) until attestation is solved or a caller opts into `K5`; `x_search` (the
current `SearchTimeline` query id is unrecovered behind an ESM import map) with
`K4` as the interim route; `tiktok_public`, unverified because this network
answered 503 with a login portal and `evidence.md` §"The captive-portal caveat"
forbids reading that as platform behaviour; `reddit_oauth` and
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
| `third_party_archive` | an independent archive answered, not the platform | `reddit_archive` |
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
| `auth_required` | the origin refused over who is asking, or the route needs a credential this package does not supply | `router`, `x_guest`, `linkedin_public`, `instagram_public`, `youtube_innertube`, `cli` — the router for a K5 route, the four adapters for an origin's own refusal, `cli` reading it |
| `no_route` | the core declares no such adapter or route | `router`, `runner`, for an adapter or route the core does not declare |
| `rate_limited` | the origin asked for fewer requests | `adapters`, on HTTP 429 |
| `schema_drift` | the payload arrived in a shape this parser does not know, so an empty result would have been a lie | `github_rest`, `hacker_news`, `instagram_public`, `linkedin_jobs`, `linkedin_public`, `reddit_archive`, `reddit_feed`, `rss_atom`, `web_search`, `x_guest`, `x_syndication`, `youtube_innertube` |
| `field_omitted` | the answer carried, and one declared field of the roster row was not in it | `github_rest`, `hacker_news`, `instagram_public`, `linkedin_jobs`, `linkedin_public`, `reddit_archive`, `reddit_feed`, `rss_atom`, `web_search`, `x_syndication`, `youtube_innertube` |
| `malformed_json` | the body did not parse as the JSON the route declares | `fake`, `github_rest`, `hacker_news`, `instagram_public`, `linkedin_public`, `reddit_archive`, `x_guest`, `x_syndication`, `youtube_innertube` |
| `http_status` | the origin answered with a status the route does not read as an answer | `github_rest`, `hacker_news`, `instagram_public`, `linkedin_jobs`, `linkedin_public`, `public_page`, `reddit_archive`, `reddit_feed`, `rss_atom`, `web_search`, `x_guest`, `x_syndication`, `youtube_innertube` — thirteen, which is every adapter that reads an origin |
| `withheld` | the origin declined the payload and said nothing this package can class further | `youtube_innertube`, for a playability refusal the evidence did not record |
| `engagement_unavailable` | this surface publishes no counts at all, so a zero would be a number nobody reported | `reddit_feed`, `web_search` |
| `date_precision_only` | the origin gave a date and no time, so the instant is the date's | `linkedin_jobs`, `youtube_innertube` |
| `unselected_target` | this route does not serve the selection it was asked for | `public_page`, for a selection this route does not serve |
| `native_identity_unknown` | the row carries no platform-native id, so it can never group by strong identity | `web_search`, standing on every index hit |
| `unknown_publication_time` | the row carries no publication time, so it sorts as missing | `web_search`, standing on every index hit |
| `target_not_hydrated` | this hit was discovered and nothing in this artifact hydrated it | `web_search`, standing on every index hit |
| `recall_window_partial` | the step stopped while the origin was still offering, so the set is a window and not the whole | `runner`, when a cap truncated |

Four of the names above are readers rather than emitters: `runner.reached_origin`
reads `cache_hit`, `smoke.channel_of` reads `network_intercepted` and
`unreachable`, and `cli.target_may_be_the_problem` reads `auth_required` and
`attestation_required`. Everywhere else, naming a code is attaching it.

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
