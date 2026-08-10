# super-research protocol

`SKILL.md` is the contract. This is the detail behind it: the manifest a caller
writes, the record it gets back, the ladder every route is classed on, the codes
a partial answer carries, and the orders a set may be put in. Names here are the
package's own — a term in `code` is a name the source spells exactly that way.

## What the evidence says, and what it does not

The routes below were measured on 2026-08-10 from one macOS host,
unauthenticated, and recorded in
`.orch/runs/20260810T092133Z-keyless-acquisition/findings.md` §1: status, latency,
and the field names each payload actually carried. That measurement predates this
package. **The parsers in it have never read a live origin.** Every ceiling,
field list, and route constant here traces to that one host at that one moment;
the offline suite runs the parsers against the payloads those probes recorded,
which is a statement about those fixtures and not about any origin today.

Two consequences a caller must carry:

- `python3 -m super_research.cli status` reports every adapter `unverified` on a
  fresh checkout, because the smoke ledger starts empty. That is the honest
  reading of the evidence, not a fault to route around.
- `findings.md` §0 records that the measuring host sits behind an appliance that
  answers some domains with HTTP 503 and a `<base href="/login/">` body. A read
  that comes back `network_intercepted` is a statement about the asking network.
  It never degrades an adapter and never becomes a platform gap.

## Layout

`scripts/super_research/`, standard library only on the Python 3.9 floor, no I/O
at import time. The module set is not the one the frozen spec's affected surfaces
list: `ledger.py`, `ordering.py` and `pacing.py` were split out of `runner.py`,
and `probes.py` and `smoke.py` out of `cli.py`, after the spec froze.

| module | owns |
| --- | --- |
| `schema.py` | closed enums, the immutable manifest and artifact values, `parse_manifest` |
| `transport.py` | every route constant, every `K1` public client credential, the guest-token store, the captive-portal detector, `route_admissions` |
| `router.py` | one step's route decision, from per-route booleans alone |
| `runner.py` | literal adapter dispatch, and one manifest run to one artifact plus its ledger |
| `pacing.py` | per-route budgets and the rate governor |
| `ledger.py` | the work ledger and the schedule a mode admits |
| `ordering.py` | the five named views |
| `cache.py` | one run's TTL memory of reads it already made |
| `normalize.py` | native pages to immutable records; grouping and provenance edges |
| `project.py` | a pure bounded subset of one artifact |
| `probes.py` | the thirteen liveness probe declarations |
| `smoke.py` | one probe's read, and the standing it leaves an adapter at |
| `cli.py` | three operations, and everything an operator reads |
| `adapters/__init__.py` | `AdapterDescriptor`, `NativeRecord`, `NativePage`, `fetch_one_page` |
| `adapters/<id>.py` | one route's parser, one `DESCRIPTOR`, one `fetch_native_page` |

`runner.py` re-exports every name moved to `ledger`, `ordering` and `pacing`, and
`cli.py` every name moved to `probes` and `smoke`, so each name has one definition
and one address. Tests are `tests/`, with `tests/helpers.py` and
`tests/fixtures/**`; the whole suite runs with no network reachable.

## Manifest grammar

`schema.parse_manifest` validates totally, before any transport call, and raises
`ManifestError` on anything it cannot accept. An unknown key at any level is
rejected rather than ignored.

Manifest keys are exactly `schema_version`, `manifest_id`, `mode`, `as_of`,
`steps`.

- `schema_version` must equal `2`. There is no other manifest schema.
- `manifest_id` and `as_of` are nonempty strings.
- `mode` is `staged` or `fused`. Steps execute in declared order either way, so
  the artifact is the same artifact; the mode reaches only the schedule the
  ledger records. **Nothing in this package runs concurrently** — there is no
  thread, task, coroutine, or process anywhere in it — so `fused` overlaps
  nothing at execution time. What it collapses is the round-trip: discovery and
  bounded hydration happen in **one invocation**, where `staged` puts a caller
  between one step's output and the next step's input. That is real and it is
  the whole of the difference a caller feels. In the ledger the two are placed
  under different models — `fused` on per-step lanes bounded by each route's
  budget, `staged` on one serial line — and `fake_makespan_us` is the span of
  that placement: a modeled counterfactual, never wall clock. Either way it
  collapses latency, never lineage.
- `steps` is a nonempty sequence of steps with unique `step_id`s; a
  `prior_step_id` must name a step in the same manifest.

Step keys are exactly `step_id`, `kind`, `adapter_id`, `query`, `prior_step_id`,
`selected_hits`, `max_items`.

- `kind` is `discovery` or `hydration`. A discovery step forbids `selected_hits`
  and authorizes exactly one call. A hydration step requires them and authorizes
  one call per hit, which is what makes each hydration record's provenance exact
  rather than inferred.
- Each hit is exactly `{discovery_locator, target_id}`, both nonempty.
  `discovery_locator` is the normalized locator the caller saw in the discovery
  step's output; it is the only thing that ties a hydration record back to its
  discovery record, and nothing is matched by similarity.
- `max_items` is a hard positive integer cap. It is required — there is no
  default and no unbounded step. The core owns stop: no further call is made once
  the cap is met, and a step that truncated emits `recall_window_partial`.
  **Nothing pages.** `runner.planned_calls` is the only production constructor of
  an `AdapterRequest` and never sets `cursor`, so a discovery step's one call is
  its only call and `max_items` truncates inside that one page. Six adapters read
  a cursor and five surface `cursor_out`; that is the seam a later core would
  page through, and until one does, "the core owns pagination" names an owner
  rather than a behaviour.

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

The superseded spec's retention family is absent by design: this package owns no
store, writes no artifact, and has no delete primitive, so there is nothing for a
retention deadline to govern. The one file anything here writes is the smoke
ledger, outside every working tree.

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
2. A `K1` public client credential is a route constant `transport.py` owns. It is
   attached at send time, never enters a manifest or an artifact, and is stripped
   back off the answering address before that address leaves the transport seam.
3. A `K3` route is labelled with its operator identity and carries
   `third_party_archive` on **every record**. The label has to be on the row:
   `normalize.normalize_page` builds a record's loss from that native record's
   own and never from the page's, so an archive that labelled only the page
   would leave an artifact whose rows all read as the platform speaking.
4. A `K4` discovery hit and its hydrated target are linked, never merged.

`AdapterDescriptor.__post_init__` refuses any `access_class` not in
`schema.ACCESS_CLASSES` at construction, because three separate rules read it —
the router admits on it, `time_confidence_for` decides on it, and the artifact
publishes it — and none can tell an unnamed class from a wrong one.

**No route in this package is `K5`, and there is no lawful shape for one.** A
credentialed surface beside a keyless one on the same adapter breaks one class per
adapter; a wholly credentialed adapter breaks rule 1, because the core substitutes
nothing and a caller naming that adapter is simply refused. The ladder's two named
`K5` members, Reddit OAuth and the YouTube Data API, are deferred for that reason
rather than by coincidence.

`transport.route_admissions()` is the only route knowledge the router ever sees:
one boolean per route, true exactly when the route's class is not `K5`. The router
sees no host, path, or credential, and answers `no_route` or `auth_required`
before any I/O.

## Adapter roster

Fourteen adapters, thirteen live plus `fake`; seventeen route surfaces, because
three adapters read more than one. Read back off `runner.surface_descriptors`.

| adapter | class | route surfaces | what ships |
| --- | --- | --- | --- |
| `web_search` | `K4` | `ddg_html` | DDG HTML discovery: title, locator, snippet |
| `public_page` | `K0` | `public_page_article`, `public_page_control` | one selected static document: body, hash, links, content type, requested and final address |
| `reddit_archive` | `K3` | `arctic_shift_posts_ids` | Arctic Shift hydration by submission id: title, author, subreddit, permalink, created time, `score`, `num_comments` |
| `reddit_feed` | `K0` | `reddit_feed` | subreddit RSS freshness probe: title, locator, author, updated. No engagement |
| `x_syndication` | `K2` | `x_syndication_timeline` | one handle's timeline from the page's own `__NEXT_DATA__`, with the platform's four counts |
| `x_guest` | `K1` | `x_guest_graphql` | guest token then `TweetResultByRestId`, `UserByScreenName`, `UserTweets` |
| `linkedin_public` | `K2` | `linkedin_public_profile` | `/in/<slug>` `ld+json` Person: name, description, `jobTitle`, `addressLocality`, `worksFor`, `alumniOf` |
| `linkedin_jobs` | `K0` | `linkedin_jobs_guest_search` | `jobs-guest` search: URN id, title, company, posted date |
| `youtube_innertube` | `K1` | `youtube_innertube` | `search`, `next` comment threads, `player` metadata. No captions |
| `instagram_public` | `K1` | `instagram_web_profile` | `web_profile_info`: biography, follower count, recent posts with like and comment counts |
| `hacker_news` | `K0` | `hn_algolia_search`, `hn_firebase_item` | Algolia search for stories and comments, plus Firebase v0 item and `kids` traversal |
| `github_rest` | `K0` | `github_rest`, `github_search` | anonymous repositories, issues, releases, search |
| `rss_atom` | `K0` | `youtube_channel_feed` | one generic RSS 2.0 and Atom parser: identity, dates, enclosures, transcript links |
| `fake` | `offline` | `fake_offline` | deterministic fixture pages. Never live evidence, and the one adapter with no smoke |

`rss_atom` is a generic feed parser bound to one declared route. A second feed is
a second route constant in `transport.py`, not a caller-supplied address; the
adapter never names a host.

Deferred, each with a reopen condition rather than a silent drop: `youtube_captions`
(PoToken attestation; `captionTracks` was empty on five clients across three
videos) until attestation is solved or a caller opts into `K5`; `x_search` (the
current `SearchTimeline` query id is unrecovered behind an ESM import map) with
`K4` as the interim route; `tiktok_public`, unverified because this network
answered 503 with a login portal and §0 forbids reading that as platform
behaviour; `reddit_oauth` and `youtube_data_api` as `K5` throughput upgrades.

## Five capabilities that ship smaller than their roster row

Stated here because a reader comparing the shipped package to the frozen spec's
roster would otherwise find the gap by being wrong about it. This list asserts
completeness — five, not "some" — and it is the third enumeration in this file
that does, so `test_dependency_boundary` counts its entries against the number
in the heading. An earlier revision said two and had five.

1. **`linkedin_public` reads `/in/<slug>` only.** The spec's row reads
   "profile/company". `findings.md` §1 records `linkedin.com/company/<slug>`
   answering 200 with a marker name and **no field set**, so a company parser
   would be inferred rather than measured. `linkedin.com/company/<slug>` is a
   different path and would be a different route constant.
2. **`reddit_archive`'s smoke omits `upvote_ratio` and `selftext`.** The spec's
   row names both, and they fail its assertion for different reasons.
   `upvote_ratio` is a float where `EngagementSnapshot.value` admits only exact
   integers, so it is carried nowhere on the record. `selftext` *is* carried — it
   is the record's `body` — but a link submission has none, so asserting it would
   fail a healthy read. The gate may yet close the first through `attributes`;
   until it does, the smoke asserts the seven fields the inventory below lists,
   and the roster row names more than the shipped adapter carries.
3. **`web_search` ships DuckDuckGo and no second provider.** The spec's row
   commits "Brave/Bing as declared secondary providers with per-provider
   parsers". Neither ships: `transport.py` declares one web-index route and
   `web_search.py` holds one parser. `findings.md` §1 measured both answering
   200 and resisting extraction — Brave with obfuscated class names, Bing with
   markup no clean triple came out of — so a parser for either would be written
   against markup nobody has extracted from rather than against a measurement.
   Reopen when one of them yields a title/locator/snippet triple on a probe.
4. **`reddit_archive` ships one Arctic Shift route of the four the spec names.**
   The row names `posts/search`, `comments/search`, `posts/ids` and `comments`
   by `link_id`. Only `posts/ids` is delivered, which is hydration by exact id,
   so **all Reddit discovery through the archive is absent** — `reddit_feed`'s
   one-per-30 s RSS and `K4` are the discovery this package has for Reddit. This
   is also why `scope_required` and `archive_lag` are named in the loss
   vocabulary and emitted nowhere: the routes where a scope grammar and a lag
   window would be observable are the three that are not here.
5. **`rss_atom` is a generic parser bound to one route.** The row reads
   "Generic RSS/Atom", and the parser is: it reads RSS 2.0 and Atom, identity,
   dates, enclosures and transcript links. What it cannot do is point anywhere
   — a feed is a route constant `transport.py` owns, and one is declared,
   `youtube_channel_feed`. The adapter names no host, so a second feed is a
   second constant and not a caller-supplied address. That is the non-goal about
   generic HTTP primitives holding, and it is still less than the row implies.

## Rate budgets, cache, and the work ledger

**Per-route budgets replace a uniform cap.** Each descriptor declares
`min_interval_ms`, `burst` and `cooldown_ms` as measured constants, enforced per
route by `pacing.RateGovernor`. A ceiling belongs to the origin, so two adapters
reading one route declare the same three numbers. An undeclared route takes
`DEFAULT_MIN_INTERVAL_MS=1000`, `DEFAULT_BURST=1`, `DEFAULT_COOLDOWN_MS=60000`: a
limit nobody has measured is not one to spend. The measured extremes are
`reddit_feed`, at one read per 30 000 ms, and `github_rest`, whose anonymous hour
is sixty reads in each of two separately counted buckets — which is why its two
surfaces are two routes rather than one.

**The composition is the default, not an option a caller assembles.**
`runner.run_acquisition(manifest)` and `run_scheduled` name no carrier and get
`pacing.paced_carrier`: a `RateGovernor` over a `RunCache` over a real
`transport.Transport`, all three on the run's own clock. It is the only place in
the package that builds a carrier, which is checkable from outside — a second
one is a second unpaced door. Handing in a carrier is how a caller takes pacing
over deliberately; there is no way to reach an origin unpaced by omission.

An HTTP 429 is typed `rate_limited` on the page, sets that route's cooldown, and
ends the call. It never triggers a second read, another route, or a changed
identity: `transport.USER_AGENT` is one static string, and a rate limit is a
constraint this package respects rather than evades.

**The run-local cache is a correctness requirement**, not an optimization: at one
to two reads per thirty seconds, a run that re-reads a Reddit feed starves.
`cache.RunCache` is keyed by `(route_id, canonical_request)`, holds at most
`MAX_ENTRIES=64` bodies of at most `MAX_ENTRY_BYTES=512 KiB`, runs on a monotonic
clock, and dies with the run — `close()` makes a later run's reach for it an error
rather than a quiet hit. Per-route TTLs are declared in `ROUTE_TTL_SECONDS`;
`public_page_control` declares `0.0`, because a channel control answered from
memory would report the network healthy on the strength of a read made before the
appliance woke. A served entry carries `cache_hit` on the page and on every
record, and keeps the transport's own `observed_at` — a cached record states when
the origin was read, never when memory answered.

**The work ledger** is additive per-operation deltas in one causal order, keyed
`(dispatch_ordinal, operation_ordinal, operation_kind_ordinal, metric_ordinal,
operation_id)`. This core schedules one operation kind, `native_page`, and emits
`calls`, `pages`, `items` and `fake_duration`, plus one zero-delta `stop` marker
per dispatch naming why the run ended. `pages` is emitted exactly once per
operation, because one native page per adapter call is the law. `fake_makespan_us`
is derived over the schedule and is deliberately not a metric: two operations the
model places overlapping count once between them, which is the only quantity that
tells `fused` from `staged`. It is a counterfactual over a placement, not a
measurement of a run — nothing in this package executes two operations at once.

## Failure and loss vocabulary

Loss is typed and additive: a code says what is missing or how the answer was
qualified, and an outcome says how the read ended. They are read together. A
record carrying a loss code is not a failed read — `youtube_innertube` returns
`ok` with `attestation_required` when a player withholds caption tracks and still
carries the metadata it did get.

**Both tables below are read back off the source, never transcribed into it.**
`test_dependency_boundary.LOSS_VOCABULARY` parses these two tables out of this
file and compares each row against what the package's own syntax says, so a cell
that stops being true is a red test rather than a sentence nobody re-read. The
same treatment `THREAT_REMAP` gets, and for the same reason: an earlier hand-kept
count said three emitters where there were thirteen.

The **named by** column is every module whose executable code spells that code,
to attach it or to read it. Spelling is the property worth pinning, because the
defect it prevents is a name with two spellings: a module-level constant in one
file and a bare literal in another means one search finds neither half. Three
entries are readers rather than emitters and are named as such below the tables.
A module that only declares a constant and never loads it is not named — that
absence is itself a claim, and it is checked too.

The seven codes this delivery adds to the retained vocabulary:

| code | means | named by |
| --- | --- | --- |
| `third_party_archive` | an independent archive answered, not the platform | `reddit_archive` |
| `stale_identifier` | a vendor identifier rotated; the read was refused, not empty | `x_guest` (404), `youtube_innertube` (400) |
| `attestation_required` | the origin withheld a payload behind an attestation this package does not perform | `youtube_innertube`, for the two playability statuses findings.md §1 measured and for a withheld caption list |
| `network_intercepted` | the local network answered, not the origin | `transport`, `adapters`, `smoke` |
| `cache_hit` | this run's own memory answered | `adapters`, `runner` |
| `archive_lag` | an archive's coverage trails the platform | nothing: **absent from the source entirely** |
| `scope_required` | an archive query needs a scope it was not given | nothing: **absent from the source entirely** |

`third_party_archive` is on the row and not on the page.
`normalize.normalize_page` builds a record's loss from that native record's own
and never from the page's, so an archive labelling only the page would leave an
artifact whose rows all read as the platform speaking — which is why rule 3 of the
access ladder says every record.

`archive_lag` and `scope_required` are named in this table and nowhere else in the
delivery: not emitted, and not declared either. The one Arctic Shift route
delivered is `posts/ids`, which is hydration by exact id and takes no scope;
`posts/search`, `comments/search` and `comments` by `link_id` — where the spec's
grammar rule that `title=` requires `subreddit` or `author` lives, and where a lag
window would be observable — are not shipped. The two codes are named here so a
later route adds a code the vocabulary already has, and so nobody reads their
absence from the source as the vocabulary being smaller than the spec says.

The retained codes, and every module that spells one:

| code | named by |
| --- | --- |
| `auth_required` | `router`, `x_guest`, `linkedin_public`, `instagram_public`, `youtube_innertube` — the router for a K5 route, the four adapters for an origin's own refusal |
| `no_route` | `router`, `runner`, for an adapter or route the core does not declare |
| `rate_limited` | `adapters`, on HTTP 429 |
| `schema_drift` | `github_rest`, `hacker_news`, `instagram_public`, `linkedin_jobs`, `linkedin_public`, `reddit_archive`, `reddit_feed`, `rss_atom`, `web_search`, `x_guest`, `x_syndication`, `youtube_innertube` |
| `field_omitted` | `github_rest`, `hacker_news`, `instagram_public`, `linkedin_jobs`, `linkedin_public`, `reddit_archive`, `reddit_feed`, `rss_atom`, `web_search`, `x_syndication`, `youtube_innertube` |
| `malformed_json` | `fake`, `github_rest`, `hacker_news`, `instagram_public`, `linkedin_public`, `reddit_archive`, `x_guest`, `x_syndication`, `youtube_innertube` |
| `http_status` | `github_rest`, `hacker_news`, `instagram_public`, `linkedin_jobs`, `linkedin_public`, `public_page`, `reddit_archive`, `reddit_feed`, `rss_atom`, `web_search`, `x_guest`, `x_syndication`, `youtube_innertube` — thirteen, which is every adapter that reads an origin |
| `withheld` | `youtube_innertube`, for a playability refusal the evidence did not record |
| `engagement_unavailable` | `reddit_feed`, `web_search` |
| `date_precision_only` | `linkedin_jobs`, `youtube_innertube` |
| `unselected_target` | `public_page`, for a selection this route does not serve |
| `native_identity_unknown` | `web_search`, standing on every index hit |
| `unknown_publication_time` | `web_search`, standing on every index hit |
| `target_not_hydrated` | `web_search`, standing on every index hit |
| `recall_window_partial` | `runner`, when a cap truncated |

Two of the names above are readers rather than emitters, and the distinction is
worth keeping: `runner.reached_origin` reads `cache_hit` to decide whether a page
cost an origin a read, and `smoke.channel_of` reads `network_intercepted` to
decide which exit code an operator gets. Everywhere else, naming the code is
attaching it. Two modules declare a code as a constant and never load it, which
is the same shape the four keyless adapters have for `auth_required`:
`transport` owns `rate_limited` for `adapters.fetch_one_page` to attach, and
`cache` owns `cache_hit` for `adapters._served_from_cache` to attach.

A cell holds module names in backticks and nothing else in backticks, because
the test reads it that way: a term of art or a count belongs in the prose beside
the names.

`reddit_feed`, `rss_atom`, `public_page` and `github_rest` each declare
`AUTH_REQUIRED` and load it nowhere. That is the statement, not an oversight: no
status those documented-keyless routes can answer with is a report that a
credential was needed, and a name with zero loads makes it checkable from outside
the module — which the same test checks, in that direction too. `hacker_news`
does not declare it at all.

A route that fails does not fall back. `schema_drift` and `stale_identifier` exist
so that a changed payload is a typed failure rather than an empty success, which
is the one outcome a caller cannot tell from "there is nothing there".

## Ordering contract

Five named views, in `ordering.ORDERING_CONTRACT`: `newest`,
`cross_source_chronology`, `native_top`, `most_commented`, `most_replied`. Ask for
anything else and `order_records` raises `OrderingError`.

Four of the five — every one but chronology — rank inside a single
`(platform, canonical_content_kind)` family and **refuse a mixed set** rather than
ranking a Reddit post against a web hit. Chronology crosses source roles on
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

## Two laws, each bought with a defect

Neither is derivable from the code by a reader who has not already made the
mistake, so both are stated as law.

### A record's route, not its adapter, identifies the surface that produced it

An adapter id names a parser. A route id names the surface a read actually left
on. Every accounting and every metric lookup keys on the route.

- `StepResult.route_id` and `WorkLedgerEvent.route_id` are `page.route_id` — the
  route the page says answered — and not the route the core routed by. A step
  whose pages disagree on a route falls back to the route it was admitted on,
  because no single route is what it read and each record already carries the
  exact one it came from.
- `ordering._surface_descriptor` resolves a metric name by matching the record's
  `route_id` against the descriptors `runner.surface_descriptors` returns for that
  adapter, and only then falls back to the adapter's own.

Charging to the adapter is invisible until an adapter reads two surfaces. It bills
one origin's budget for the other's read, and it resolves `most_commented` by
adapter id alone — so one surface's rows get ranked by the other surface's metric
name, and half a view goes unranked. Hacker News is where this shows: the item
store calls a story's comment count `descendants` and the index calls the same
quantity `num_comments`, and neither is this package's to rename. `github_rest`
has the same shape, with one anonymous hour counted in two buckets.

### A page is not a call

A page is what an adapter returned. A call is what an origin was asked to spend.
`runner.reached_origin` is the one place that decides, and it is false in **two**
ways: the run's own memory answered (`cache_hit`), or the adapter refused before
making a call at all (`outcome == "refused"`). `refused` is the one outcome
meaning the read never left; every other one, failures included, describes
something an origin or the local network actually answered.

Inferring "reached the origin" from "not a cache hit" is indistinguishable from
correct until an adapter can refuse *without* calling — a target it does not
serve costs a page and no read. Once one can, the ledger bills a `calls` delta for
a request that never went out, and every downstream sum is wrong by the number of
refusals. `public_page`'s refusal of an unserved selection is the case that
exposed it.

## What the package refuses

Threat oracles T01–T16 are retained from the superseded spec with applicability
remapped from `A0`–`A5` to `K0`–`K5` by the rule the old mapping used: a threat
applies to a class when that class has the machinery the threat is about. The
remap table is `test_transport.THREAT_REMAP` and is itself checked — every threat
named once, every class one the ladder declares, and every class the roster
answers at covered by at least one threat. `offline` is not on the ladder; nothing
about `fake` is a claim about a route.

| threat | applies to | form here |
| --- | --- | --- |
| T01 | `K1`, `K5` | no credential id or value reaches a request, a response, a call log, or an artifact |
| T02 | `K1`, `K5` | the address a query-placed key was appended to comes back stripped |
| T03 | `K1`, `K5` | a credential is attached at send time from the route's own constant, so it reaches that origin and no other |
| T04 | `K0`–`K5` | no route admits a state-changing verb |
| T05 | no class | no process is launched, because none can be |
| T06 | `K0`–`K5` | a caller cannot escape a route's admitted method set, and a body is the route's shape with the caller's values |
| T07 | no class | no session state to export: the one token a run mints lives in memory |
| T08 | no class | nothing navigates, clicks, or submits |
| T09 | `K0`–`K5` | acquired text is `untrusted_content`: it changes no plan, no grant, no write set |
| T10 | `K1`, `K5` | a `K1` credential names no user, so there is no principal to mismatch; the operator that answered is declared |
| T11 | `K0`–`K5` | a refusal is typed `rate_limited` on one call, and no identity changes |
| T12 | `K0`–`K5` | a route the run cannot reach is refused with a typed reason and never probed |
| T13 | `K4` | an index surface declares itself an index, and is the only surface that does |
| T14 | `K0`–`K5` | no delete primitive: the only stores are in memory |
| T15 | `K0`–`K5` | a refusal costs the origin nothing: it is decided before any call |
| T16 | `K0`–`K5` | no fallback: a failed read is a typed failure, never a second read elsewhere |

T05, T07 and T08 apply to no class because the `K0`–`K5` ladder has neither an
ambient-identity CLI nor an exported browser session; they are answered by absent
machinery rather than by a behaviour, and recording that is the remap.

**Zero writes are reachable.** `transport.admitted_methods` returns `GET` and
`HEAD` for every route but two named exceptions, both POSTs that create nothing:
minting an anonymous guest token, and asking InnerTube a question it publishes no
GET form for. A query-body route's body is rendered from that route's declared
`body_params` and from nothing else, so a caller supplies values into a shape this
module owns and can never choose the shape — the point at which a route would
become the generic HTTP primitive the spec's non-goals refuse. PUT, PATCH and
DELETE are admitted by no route, unconditionally. The opener also refuses any URL
that is not `https://`.

**Everything acquired is untrusted content.** A snippet, a body, an attribute
value, or a profile description is data. It never alters a manifest, a route, a
cap, or a write set, however it is phrased, and the calling lane owes it the same
treatment.

## CLI surface

`python3 -m super_research.cli`, with this item's `scripts/` on `PYTHONPATH`.
Three operations, one argument, fifteen reachable invocations. The parser is built
from the `OPERATIONS` table, so the enumeration a reader checks is the one the
parser was made from.

| operation | argument | reaches an origin | writes | exit |
| --- | --- | --- | --- | --- |
| `adapters` | none | no | nothing | 0 |
| `smoke` | `--adapter <one of thirteen>`, required | one bounded read | its own ledger, only on success | 0 / 1 / 3 |
| `status` | none | no | nothing | 0 always |

No operation takes an address, a route, a path, a manifest, or a command;
`--adapter` is a closed `choices` list of the thirteen live ids. `fake` is refused
with everything else: reading a fixture and printing it as liveness is the one
result this surface must never produce. The carrier, clock, moment, ledger path
and output stream are parameters of `main` with the real defaults and are
unreachable from a command line, which is how the whole path is exercised offline.

Exit codes: `0` the roster row was carried; `1` the origin answered and the row was
not carried; `2` argparse's own usage error, taken by nothing else here; `3` this
host's local network answered, **or nothing answered at all**, so nothing about
the platform was concluded. `1` and `3` are separate doors because they are not
the same news. A refused connection, an unresolvable name, or a TLS failure
raises `TransportError` out of the opener rather than becoming a typed page,
because there was no answer to type; `cli.main` catches it and takes `3`, and
records nothing. Letting it leave as a traceback would take `1` — a cable
nobody plugged in, filed as a row the origin declined to carry.

Two dispositions and no third: `verified` and `unverified`. Rejecting a platform
is not something this package does from one read, so `rejected` is not in the
vocabulary at all and "never degrades to rejected" is structural rather than a
branch someone has to remember. Reasons are `fresh_success`, `never_smoked`,
`stale_success`, `unreadable_last_success`, `last_success_ahead_of_now`. The
window is seven days, because every route here depends on markup or on a vendor
identifier that rotates without notice. The ledger is one JSON object of adapter
id to ISO stamp at `<tempdir>/super-research/smoke-ledger.json`, a constant no
argument can point elsewhere.

The ledger only ever gains an entry. A read that carried its whole row, from the
origin, stamps that adapter; a blocked read is not a finding about the platform,
and a failed read has not undone a success already recorded. Expiry happens by the
window passing, never by a later read revoking an earlier one. An unreadable
ledger reads as empty, which makes every adapter `unverified` — the only safe
direction.

## Smoke inventory

One probe per live adapter, in `probes.py`. Each is one ordinary manifest step,
not a private path into an adapter, and its assertion is that **one record of the
named kind carries the whole list** — a row assembled out of several records would
claim a completeness no single answer had. `engagement:` and `attribute:` prefixes
name the two places a route's own vocabulary lands.

| adapter | route | probe | field set asserted |
| --- | --- | --- | --- |
| `web_search` | `ddg_html` | discovery `rate limiting` | web_hit: title, canonical_locator, body |
| `public_page` | `public_page_article` | hydration `article:Rate_limiting` | web_page: body, exact_content_hash, observed_at, attribute:content_type, attribute:link, attribute:requested_url, attribute:final_url |
| `reddit_archive` | `arctic_shift_posts_ids` | hydration `z1c9z` | post: title, author, community, canonical_locator, published_at, engagement:score, engagement:num_comments |
| `reddit_feed` | `reddit_feed` | discovery `programming` | post: title, author, canonical_locator, published_at |
| `x_syndication` | `x_syndication_timeline` | hydration `simonw` | post: body, published_at, native_parent_id, engagement:favorite_count, engagement:retweet_count, engagement:reply_count, engagement:quote_count |
| `x_guest` | `x_guest_graphql` | hydration `user:simonw` | profile: native_item_id, title, author, canonical_locator, published_at, engagement:followers_count |
| `linkedin_public` | `linkedin_public_profile` | hydration `williamhgates` | profile: title, body, attribute:jobTitle, attribute:addressLocality, attribute:worksFor, attribute:alumniOf |
| `linkedin_jobs` | `linkedin_jobs_guest_search` | discovery `reliability engineer` | job_posting: native_item_id, title, author, published_at |
| `youtube_innertube` | `youtube_innertube` | hydration `dQw4w9WgXcQ` | video: title, published_at, engagement:viewCount |
| `instagram_public` | `instagram_web_profile` | hydration `instagram` | profile: title, author, body, engagement:edge_followed_by.count; **and** post: native_item_id, published_at, engagement:edge_liked_by.count, engagement:edge_media_to_comment.count |
| `hacker_news` | `hn_algolia_search` | discovery `python` | story: title, author, published_at, engagement:points, engagement:num_comments |
| `github_rest` | `github_rest` | hydration `python/cpython` | repository: title, body, author, published_at, engagement:stargazers_count, engagement:forks_count, engagement:open_issues_count |
| `rss_atom` | `youtube_channel_feed` | discovery `UC_x5XG1OV2P6uZZ5FSM9Ttw` | feed_entry: native_item_id, title, author, canonical_locator, published_at |

Instagram's is the only row describing two content kinds, which is why a field set
is declared per kind at all: no single record carries both the profile's follower
count and a post's like count. Three adapters read two surfaces each and a smoke
makes one call, so each probe names the surface it takes — Algolia search for
`hacker_news`, the repository surface for `github_rest`, the article surface for
`public_page`.

A probe target can rot without the route changing, and a removed target and a
broken route both come back with no row. Every probe whose target is a named item,
slug, channel, or handle therefore declares `target_recovery`: how to obtain a
current one. A query never goes stale and declares none.
