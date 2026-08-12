# Lane 02 — social and community acquisition

- `run`: `20260809T154721Z-super-research`
- `ticket`: `02-social-community`
- `executor`: `orch-investigate`
- `independence`: blind; no sibling lane was read
- `frozen_spec_sha256`: `4952B1695DC3296203B74720C65E08616DFEDCB56BDEA09D8CD51090BC3CDB89` (verified before research)
- `observed_at`: `2026-08-09` (Asia/Singapore)
- `source_policy`: current official API documentation, platform policy/help, and pinned official source only
- `status`: corrected after research-lens block

## Bound audit

This corrected packet retains exactly 14 actual primary artifacts, identified individually as S1–S14. It cites no collection, repository, documentation site, or paired pages as one disguised source. The blocked packet at SHA-256 prefix `13A112…` referenced 26 artifacts and is superseded; claims that depended only on its additional artifacts were removed or converted to explicit gaps. The correction pass added no substantive source read. The final evidence set uses 14 substantive artifact reads; line-targeted continuation within the same artifact does not create another source identity. Failed renderer/cache probes are dead ends and support no finding.

## Verdict

The smallest defensible live set from this lane is:

- initial complete-enough community adapter: Hacker News;
- initial schema-unverified questions discovery adapter: Stack Exchange, with explicit query/date/sort and quota handling;
- conditional initial Bluesky post discovery: search results, native IDs, index time, and engagement are supported, but thread retrieval and publication-time extraction remain feature gaps under this lane's pruned source set;
- conditional initial Mastodon known-status/thread hydration: exact status/reply fields and bounded context are supported, but discovery-list pagination and common rate defaults are feature gaps;
- gated adapters: Reddit, X, and Discourse.

Reddit requires registered OAuth and an approved use, while its current generated API reference does not define exact Link/Comment date and engagement response fields. X requires developer credentials and pay-per-use capacity; the retained artifacts define search, fields, and billing but not current endpoint rate constants or a complete conversation-search contract. Discourse's pinned OpenAPI requires `Api-Key` and `Api-Username` on the relevant topic/post routes. No search-index or page fallback can counterfeit native comments, engagement, edit state, or completeness.

## Access ladder

`Public structured` is an official response contract callable without a user secret according to a retained artifact. `Credentialed` is an official application/user authorization path. `Session` means only a separately approved user-authorized read-only connector; it never means automating an ordinary login. `Page/feed` is a publisher-exposed public representation under target policy. `Search fallback` discovers locators only.

| Platform | Public structured route | Credentialed route and custody | Page/feed or search fallback loss | Disposition |
|---|---|---|---|---|
| Reddit | None admitted. Current help says clients must use registered OAuth and non-OAuth Data API traffic will be blocked [S2]. | Registered app OAuth/application-only OAuth or least-privilege user OAuth. Token remains caller-owned. | May lose `t1_`/`t3_` identity, unresolved comment branches, native engagement/date fields, deletion state, and listing cursors. | Gated. |
| X | None admitted for native structured posts. | Developer Project/App bearer or user OAuth; credits and tokens remain external caller state [S4][S6]. | Loses edit lineage, parent references, complete conversation membership, metrics, pagination, protected/withheld state, and coverage. | Gated and cost-metered. |
| Hacker News | Official Firebase v0, near-real-time, unauthenticated; retained README states there is currently no rate limit [S7]. | None required for retained reads. | Search/page results lose ranked `kids`, `parent`, `dead`/`deleted`, changing `score`, and tree completeness. | Initial. |
| Bluesky | `app.bsky.feed.searchPosts` is an official query, but its contract allows some providers to require authentication [S8]. Public availability is capability-probed rather than assumed. | Provider/PDS auth, when required, is a separate read-only custody class. No password-login automation. | Loses AT-URI/CID, `indexedAt`, native counts, blocked/not-found states, and reply-tree shape. | Conditional initial for search Posts; thread feature not admitted. |
| Mastodon | Public-status context is public within documented caps; private or expanded context requires a user token [S11]. | User token with `read:statuses` only when requested and authorized; instance host is part of custody and identity. | Loses instance-local ID semantics, federation scope, visibility/edit state, complete replies, and native counts. | Conditional initial for known-status/thread hydration. |
| Discourse | Not admitted. Pinned OpenAPI marks topic and specific-post routes as requiring `Api-Key` and `Api-Username` [S12]. | Instance-issued read-only key/username; plugins and instance policy may narrow access. | Public HTML/feed loses `post_stream`, post IDs, reply edges, versions, hidden/deleted state, metrics, and deterministic pagination. | Gated. |
| Stack Exchange | API v2.3 question reads are public under the documented quota behavior [S13][S14]. | Not admitted; exact app-key and user-token effects are gaps. Any future secrets remain caller-owned. | Page/search results cannot establish the API response schema, nested answer/comment hydration, paging, quota/backoff state, or native question ordering. | Initial for schema-unverified question discovery only. |

Only Discourse and Stack Exchange are retained as mechanism-distinct adjacent forums. Discourse is an independently configured topic/post stream; Stack Exchange is a centralized multi-site questions API with date/tag/sort controls and separately documented quota/backoff behavior. No other forum family is asserted by this lane.

## Exact platform contracts

### Reddit

Discovery and hydration [S1]:

- OAuth listing routes use `after`, `before`, `limit`, `count`, and optional `show`. Response `after`/`before` anchors are pagination lineage; listings are mutable slices rather than page numbers.
- Native identities are fullnames: `t3_<base36>` for a Link/submission and `t1_<base36>` for a Comment. Preserve the prefix; an unprefixed base-36 value is not globally typed.
- A selected submission's comment tree is requested by the documented comments route using the base-36 `article` ID. `comment`, `context`, `depth`, `limit`, `sort`, and `showmore` bound the view; the reference names `/api/morechildren` for unresolved branches.
- Native sorts include comment `confidence`, `top`, `new`, `controversial`, `old`, `random`, `qa`, and `live`; listing sorts and time windows remain within-Reddit attention views.

Schema boundary: S1 defines endpoints, types, fullnames, cursors, and comment controls but does not define current Link/Comment response fields for publication or engagement. It contains no authoritative `created_utc`, `score`, or `ups` response schema. Therefore those field names are not frozen here. Date/engagement extraction remains `schema_unknown` until an approved OAuth fixture records exact current fields, optionality, deleted/redacted payloads, and observation-time behavior. Missing schema is never coerced to zero.

Access, terms, rate, and custody [S2][S3]:

- Clients must authenticate with a registered OAuth token and a truthful descriptive User-Agent. Eligible free use is 100 QPM per OAuth client averaged over ten minutes; response headers are `X-Ratelimit-Used`, `X-Ratelimit-Remaining`, and `X-Ratelimit-Reset` [S2].
- Non-OAuth traffic may be blocked. No anonymous JSON retry or session fallback follows an auth/policy failure.
- Deleted posts/comments and deleted-account identifiers must be removed; S2 recommends routinely deleting stored user data/content within 48 hours.
- S3 requires permitted Access Info, prohibits exceeding/circumventing controls, reserves fees/separate agreements for commercial or excess use, constrains retention to approved use, and requires deletion on termination.

Typed failures: `auth_required`, `app_not_approved`, `rate_limited(reset)`, `policy_denied`, `target_deleted`, `comment_branch_partial(more_fullname)`, `schema_unknown`, `listing_drift`.

Recommendation: gated adapter discovers bounded listings, then hydrates only selected comment trees. Avoided work: one comment-tree call and all unselected comment content/model work per rejected submission. Falsifier: an approved fixture where root-only selection excludes the answer-bearing thread or current response fields cannot be schema-validated.

Confidence: high for access, cursors, identities, rate, retention, and terms; explicitly unverified for current response date/engagement names.

### X / Twitter

Search and fields [S4][S5]:

- `GET /2/tweets/search/recent` covers the last seven days and returns up to 100 Posts per request. `GET /2/tweets/search/all` covers the archive and returns up to 500 per request under its paid/Enterprise access [S4]. Search is paginated, and S5's response contract shows `meta.next_token`/`previous_token`; preserve each token and requested interval.
- Default Post fields are `id`, `text`, and `edit_history_tweet_ids`. Request only needed additions: `author_id`, `conversation_id`, `created_at`, `in_reply_to_user_id`, `referenced_tweets`, `public_metrics`, `community_id`, `lang`, and `withheld` [S5].
- `conversation_id` is the original/root Post ID. `referenced_tweets` identifies replied-to, quoted, or reposted Posts. These fields preserve available edges, but S4–S6 do not specify a complete conversation-search operator/endpoint; complete thread acquisition is therefore a gap, not an implied query.
- `public_metrics` exact names are `retweet_count`, `reply_count`, `like_count`, `quote_count`, `impression_count`, and `bookmark_count`. Store them unchanged with `engagement_observed_at`.
- `edit_history_tweet_ids` preserves version IDs. S5 does not define one authoritative `edited_at`; store edit lineage and `edited_at: unknown` unless a later admitted artifact supplies it. `created_at` is the platform creation timestamp for the returned version.

Cost and custody [S4][S6]:

- Developer account, Project/App, and keys/tokens are prerequisites [S4].
- API v2 is credit-based pay-per-use; endpoint prices live in the Developer Console, successful data-returning requests consume credits, failed requests are documented as unbilled, and the retained billing page states a two-million-Post-read monthly cap for pay-per-use plans [S6].
- Exact current endpoint rate constants and rate-header contract were removed with the excess source. They are an admission gap. A production adapter must add one current official rate artifact or treat any 429/reset headers as opaque runtime failures without claiming a numeric allowance.
- Developer terms/retention beyond S6 billing/access are also a gap.

Typed failures: `auth_required`, `access_tier_denied`, `credits_exhausted`, `monthly_cap`, `rate_limit_contract_missing`, `rate_limited`, `query_rejected`, `protected_or_withheld`, `conversation_partial`, `edit_version_missing`.

Recommendation: gated adapter uses search for bounded discovery, requests only core provenance/date/metric fields, and hydrates referenced Posts only for selected hits. Avoided work: expansions, Post reads, and model content for rejected hits. Falsifier: a common seven-day fixture where selective hydration costs no fewer billed reads or loses a referenced Post that changes the finding.

Confidence: high for retained search windows, fields and billing; low/explicitly gated for complete conversation retrieval, numeric rate limits, and non-billing terms.

### Hacker News

The pinned official README [S7] defines a public, near-real-time Firebase v0 API with no current rate limit. Items are fetched by unique integer `id`.

Exact item fields are `id`, `deleted`, `type`, `by`, `time`, `text`, `dead`, `parent`, `poll`, `kids`, `url`, `score`, `title`, `parts`, and `descendants` [S7]. `type` is `job`, `story`, `comment`, `poll`, or `pollopt`.

- Story/poll `score` is the native vote score; `descendants` is total comment count. Comments expose no score in the retained contract.
- `parent` and recursive `kids` build the comment tree. `kids` are ranked display order, not chronology or confidence.
- `time` is Unix creation time. There is no edit timestamp or revision identity: record `edited_at: unknown` and request `observed_at`.
- Discovery arrays are top/new/best (up to 500 IDs) and Ask/Show/Job (up to 200). `/v0/maxitem` supports descending discovery; `/v0/updates` exposes changed item/profile IDs. There is no page cursor, so array index or descending item position is lineage.
- `deleted` and `dead` are explicit partial/visibility states; do not erase them from the tree.

Recommendation: initial adapter reads one official ID list, hydrates bounded root candidates, date-stops roots, then recursively hydrates comments only for selected roots. Avoided work: item calls and comment/model content for rejected stories. Falsifier: a fixture where a qualifying story lies beyond the selected official list or a low-score rejected root contains the sole answer-bearing discussion.

Typed failures: `item_null`, `deleted`, `dead`, `child_missing(id)`, `tree_budget_exhausted`, `list_cap`, `no_edit_time`, `no_comment_score`. “No current rate limit” is not a capacity guarantee; concurrency stays bounded.

Confidence: high at pinned README commit `8a0528f538bca407c2ceeeefc9bee48bdb99c1c8`.

### Bluesky

The retained exact contract is intentionally narrower after source pruning [S8][S9].

- `app.bsky.feed.searchPosts` requires `q`; supports `sort` (`top` or `latest`, default `latest`), `since`, `until`, `mentions`, `author`, `lang`, `domain`, `url`, `tag`, `limit` (1–100, default 25), and `cursor` [S8].
- Output is `posts`, optional `cursor`, and optional `hitsTotal`. The contract warns the cursor may not scroll the entire result set and `hitsTotal` may be rounded/truncated. `since`/`until` use an internal `sortAt` that may differ from record creation time [S8].
- Search returns `postView`. Its required fields are `uri` (AT-URI), `cid`, `author`, `record`, and `indexedAt`; native optional snapshots are `bookmarkCount`, `replyCount`, `repostCount`, `likeCount`, and `quoteCount` [S9]. Preserve AT-URI as item identity, CID as content identity, and `indexedAt` as AppView index time.
- S9 defines `threadViewPost` as `post` plus optional recursive `parent` and `replies`, with `notFoundPost` and `blockedPost` variants. It also defines feed reply references to `root` and `parent`.

Pruned-source boundary:

- S8 says search may require authentication for some providers; this lane retains no separate host/auth artifact. Public invocation is therefore capability-probed and a provider 401/403 is terminal for that route.
- S8–S9 define the thread data shape but not the endpoint that retrieves it. Thread hydration is not admitted until one exact official endpoint artifact replaces another source within the bound or a successor spec budgets it.
- `record` is `unknown` in S9. This lane therefore does not claim the record's publication field name; `published_at` is `unknown`, while `indexedAt` and request `observed_at` remain distinct.
- Numeric rate limits, returned rate headers, provider costs, retention, and terms are gaps.

Recommendation: conditionally admit search Posts with native identity/index time/engagement and explicit `cursor_incomplete` warnings; do not claim replies or publication time. Avoided work: no thread/content hydration for rejected posts. Falsifier: a known in-window fixture omitted by cursor traversal or a provider auth response that is silently retried through another access class.

Typed failures: `provider_auth_required`, `rate_contract_missing`, `rate_limited`, `cursor_incomplete`, `hits_total_approximate`, `publication_field_unknown`, `thread_endpoint_not_admitted`, `blocked_or_not_found_shape_only`.

Confidence: high for pinned search and view schemas; explicitly incomplete for access host, publication record, thread endpoint, rate, cost, and terms.

### Mastodon

The instance origin is part of every identity. Preserve `(instance_origin, status.id)` and federation `uri`; never merge same-looking local IDs across instances.

Exact Status fields [S10]: `id`, `uri`, `url`, `account`, `content` (HTML), `created_at`, nullable `edited_at`, `visibility`, `in_reply_to_id`, `in_reply_to_account_id`, `reblog`, `quote`, `replies_count`, `reblogs_count`, `favourites_count`, and `quotes_count`. Optional viewer fields such as `favourited`, `reblogged`, and `bookmarked` depend on user context and are excluded from the public core. Counts are native snapshots at `engagement_observed_at`.

Thread hydration [S11]:

- `GET /api/v1/statuses/:id/context` returns `ancestors` and `descendants` with exact Status objects.
- Public access for public statuses is limited to 40 ancestors, 60 descendants, and depth 20. User token plus `read:statuses` supports the documented larger/private context.
- Since Mastodon 4.5, a context request may start asynchronous jobs for missing replies and return an experimental refresh header. Treat the first tree as potentially partial rather than globally complete.
- Private/missing targets share not-found behavior; preserve `private_or_missing` without inferring which.

Pruned-source boundary: this packet retains no timeline/search artifact, no common pagination artifact, and no rate-limit artifact. Mastodon is therefore admitted only as known-status/thread hydration supplied by another discovery route. Discovery coverage, page cursors, configured rate thresholds/headers, instance terms, retention, and cost remain target-instance gaps.

Recommendation: conditional initial hydrator for explicitly selected public status locators, with context node caps and instance provenance. Avoided work: context calls for unselected locators. Falsifier: two-instance fixture where the same federated URI yields different context and the adapter merges either as global completeness or omits origin/partial warnings.

Typed failures: `instance_unreachable`, `auth_required`, `private_or_missing`, `context_public_cap`, `async_refresh_pending`, `remote_status_unknown`, `rate_contract_missing`, `discovery_not_admitted`, `instance_terms_unknown`.

Confidence: high for exact Status and context contracts; explicitly incomplete for discovery, pagination, rate, and instance policy.

### Discourse

Pinned OpenAPI [S12] requires `Api-Key` and `Api-Username` for `GET /t/{id}.json` and `GET /t/{id}/posts.json`. That credentialed contract is portable; anonymous JSON behavior on an individual forum is not.

Exact topic fields: `id`, `slug`, `title`, `posts_count`, `reply_count`, `highest_post_number`, `created_at`, nullable `last_posted_at`, `bumped_at`, `like_count`, `views`, `category_id`, tags, `visible`, `closed`, and `archived` [S12].

Exact `post_stream.posts[]` evidence fields: `id`, `topic_id`, `topic_slug`, `post_number`, `post_type`, `username`, `user_id`, `created_at`, `updated_at`, `cooked`, `reply_count`, nullable `reply_to_post_number`, `quote_count`, `incoming_link_count`, `reads`, `readers_count`, `score`, `version`, nullable `deleted_at`, and `actions_summary` [S12]. `post_stream.stream` is the ordered post-ID inventory.

- Native post identity is `id`; thread position/edge is `(topic_id, post_number)` plus `reply_to_post_number`.
- `updated_at` and `version` preserve edit state. Topic `like_count`/`views` and post read/score fields remain namespaced. S12 does not contract a per-post like count inside `actions_summary`; do not invent one.
- Latest-post discovery uses `before=<post-id>` for lower-ID pagination. For a selected topic, fetch the first `post_stream.posts`, then request only missing IDs from `post_stream.stream` through the specific-post route in bounded batches.

Rate thresholds/headers, instance terms, cost, retention, and user-key scope granularity are not defined by S12 and remain admission gaps. Runtime 401/403/429 responses stay typed but no unsupported retry schedule is claimed. A read-only key and protected-category negative fixture are mandatory.

Recommendation: gated adapter discovers summaries, hydrates selected topics, then batches unresolved stream IDs. Avoided work: full topic bodies for rejected topics and one request per post. Falsifier: deleted/hidden/private fixture where batching changes order, exposes protected content, or declares completeness while stream IDs remain unresolved.

Typed failures: `api_key_required`, `scope_denied`, `instance_policy_denied`, `rate_limited_unknown_contract`, `topic_private_or_missing`, `post_stream_partial(ids)`, `post_hidden_or_deleted`, `schema_drift`, `post_like_count_unavailable`.

Confidence: high for pinned OpenAPI fields/auth/pagination; explicitly incomplete for rate, terms, cost, retention, and plugin variation.

### Stack Exchange

Question acquisition [S13]: use `GET /2.3/questions` with `site`, `fromdate`, `todate`, tags, and deterministic native sort. Supported sorts map to `last_activity_date`, `creation_date`, `score`, or native hot/week/month attention.

Retained-contract boundary: S13 establishes the `/questions` query, `site`, tag constraints, `fromdate`/`todate`, and native sort behavior. This packet does not treat S13's interactive filter surface as a frozen Question, Answer, Comment, wrapper, or paging schema.

Explicit gaps are the exact Question/Answer/Comment field sets; nested answer/comment inclusion and hydration routes; response wrapper and page fields; cursor/`has_more` stop behavior; user-private field behavior; and `content_license`. Those capabilities are not admitted until exact official artifacts or live contract fixtures fit a successor bound.

Throttle/custody [S14]:

- More than 30 requests/second from one IP is subject to a harsh concurrent throttle.
- Default daily quota is 10,000 for the applicable unauthenticated/key or user/app context.
- Any returned `backoff` seconds are mandatory for that method. Semantically identical requests should not repeat more than once per minute because of caching.

Current commercial terms/pricing, retention, private-field behavior, and content licensing are not established by S13–S14. Require a separate policy and schema preflight before production use.

Recommendation: initial adapter is discovery-only: execute bounded dated/tagged `/questions` queries under S14 throttle/backoff rules and preserve the raw response as schema-unverified. Answer/comment hydration, exact field extraction, and deterministic paging are not admitted. Falsifier: the same dated/tagged query cannot reproduce the documented sort/date constraint or the adapter ignores S14 quota/backoff behavior.

Typed failures: `quota_exhausted`, `backoff_required`, `throttled`, `field_contract_missing`, `answer_comment_contract_missing`, `paging_contract_missing`, `private_field_contract_missing`, `terms_not_preflighted`.

Confidence: high only for retained `/questions` query/date/sort behavior and S14 throttling/quota/caching/backoff; exact response schema is an explicit gap.

## Provider-neutral preservation rules

Each acquired item must preserve:

- `platform`, `upstream_instance_or_api`, native `item_id`, nullable `thread_id`/`parent_id`, canonical locator, author/community, and content kind;
- source `published_at` with confidence, nullable `edited_at`, request `observed_at`, and `engagement_observed_at`;
- engagement as exact native names, never normalized across platforms;
- discovery/hydration route, access class, upstream request identity, cursor/page/list-index lineage, requested/applied interval, warnings, and typed partial failures.

Time field map:

- Reddit: unresolved until approved current response-schema fixture.
- X: `created_at`; edit lineage through `edit_history_tweet_ids`, no retained authoritative `edited_at`.
- Hacker News: `time`; no edit field.
- Bluesky: `indexedAt` only in retained view schema; record publication field unresolved.
- Mastodon: `created_at`, nullable `edited_at`.
- Discourse: `created_at`, `updated_at`, `version`.
- Stack Exchange: the request interval and native order map to `fromdate`/`todate` and the documented sort basis; returned publication, edit, and activity fields remain schema-unverified.

Native top/hot/best orders express within-platform attention only. Popularity, provider agreement, or source count never determines authority, independence, or claim confidence. Unknown dates remain unknown. Engagement is always an observation-time snapshot.

## Failure and fallback contract

Minimum typed failure union:

- `auth_required | credential_rejected | scope_denied | policy_denied`
- `rate_limited | quota_exhausted | credits_exhausted | rate_contract_missing`
- `target_missing | deleted | private | blocked | withheld | moderation_filtered`
- `schema_unknown | field_omitted | cursor_incomplete | page_budget_stop | tree_budget_stop`
- `provider_partial | stale_index | unknown_publication_time | unknown_edit_time`

Return successful items beside route failures; one failed thread never erases other evidence. Fallback must be preauthorized by adapter contract. Search-index fallback may discover a canonical locator but cannot supply native engagement, complete comment/reply trees, deleted/private state, authoritative edit time, or native pagination. A page/feed route states every lost field. Authentication denial, credits/quota exhaustion, robots/terms restrictions, and anti-bot responses are terminal for that route. No restriction-evasion route is permitted.

## Admission matrix

| Adapter/feature | Admission | Fixture and falsifier |
|---|---|---|
| Hacker News v0 | Initial | Recent root plus recursive comments, deleted/dead child, date stop and list cap; fail if missing `kids` are hidden or a decisive low-ranked thread is excluded. |
| Stack Exchange v2.3 | Initial | Dated/tagged `/questions`, a supported native sort, and S14 quota/backoff/caching behavior; fail if a query constraint is omitted, raw schema is promoted to typed evidence, or backoff is ignored. |
| Bluesky search Posts | Conditional initial | Search with AT-URI/CID, `indexedAt`, engagement and cursor warning; fail if provider auth or incomplete cursor is silently reclassified. |
| Bluesky thread/publication | Not admitted | Requires exact official endpoint and post-record artifacts within a successor bound. |
| Mastodon known-status/context | Conditional initial | Two-instance context, edited status, public cap, private/missing target; fail if instance provenance or partial state is lost. |
| Mastodon discovery/pagination/rate | Not admitted | Requires exact official discovery and rate artifacts within a successor bound. |
| Reddit Data API | Gated | Approved OAuth, exact current Link/Comment schema, listing cursor, `more` branch, deletion/retention; fail on undocumented field assumptions or anonymous fallback. |
| X API v2 | Gated | App/credits, recent search, parent references, edit IDs, billing and current rate contract; fail if credit denial triggers page automation. |
| Discourse API | Gated | Read-only instance key, stream larger than first response, hidden/private negatives; fail on protected content exposure or hidden stream gaps. |

## Contradictions and dead ends

- Reddit S1 still marks some endpoints as RSS-capable, while current S2 warns legacy material may be outdated and requires OAuth for Data API clients. Resolution: no RSS label is treated as Data API permission; any public feed is a separate lossy route.
- X S4 says recent search is available to all developers, while S6 says API v2 is pay-per-use. These concern developer eligibility versus consumption cost, not anonymous/free access.
- The blocked packet cited additional Discourse material suggesting some public instances expose JSON. That artifact was pruned. S12's required headers are the sole retained portable contract, so anonymous behavior is no longer a finding.
- Reddit's archived OAuth wiki, empty Bluesky endpoint renderer, pinned Discourse raw cache-miss, and unofficial workaround results remain dead ends; none supports this corrected packet.

## Explicit gaps after correction

- Reddit current Link/Comment date, engagement, optionality, and deletion response schema.
- X numeric endpoint rate limits/headers, complete conversation search, and non-billing developer terms/retention.
- Hacker News edit time, comment score, formal retention/terms, and cursor pagination.
- Bluesky public host/auth rules, post publication record, thread retrieval endpoint, rate, cost, retention, and terms.
- Mastodon discovery, pagination, common rate contract, instance terms/cost/retention, and federation completeness.
- Discourse numeric rate behavior, instance terms/cost/retention, user-key scope detail, and plugin variance.
- Stack Exchange exact Question/Answer/Comment fields, nested hydration, response wrapper and paging fields, private-field behavior, content licensing, app-key/user-token effects, current commercial terms/pricing/retention, and custom-filter live behavior.
- No credentialed call, login, restricted-content request, or external mutation was performed; later local fixtures must prove credential custody and negative authorization.

## Retained primary artifacts

Mutable live artifacts were accessed `2026-08-09`. This register contains 14 links and 14 actual artifact identities.

1. **S1** — Reddit generated API reference: https://www.reddit.com/dev/api/
2. **S2** — Reddit Data API Wiki, updated 2026-05-11: https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki
3. **S3** — Reddit Data API Terms, revised 2026-07-20: https://redditinc.com/policies/data-api-terms
4. **S4** — X Search Posts introduction: https://docs.x.com/x-api/posts/search/introduction
5. **S5** — X API v2 data dictionary: https://docs.x.com/x-api/fundamentals/data-dictionary
6. **S6** — X Usage and Billing: https://docs.x.com/x-api/fundamentals/post-cap
7. **S7** — Hacker News official API README at `8a0528f538bca407c2ceeeefc9bee48bdb99c1c8`: https://github.com/HackerNews/API/blob/8a0528f538bca407c2ceeeefc9bee48bdb99c1c8/README.md
8. **S8** — Bluesky `app.bsky.feed.searchPosts` Lexicon at `f5b411d0dd998820dd363b6cf77f24be061cbd56`: https://raw.githubusercontent.com/bluesky-social/atproto/f5b411d0dd998820dd363b6cf77f24be061cbd56/lexicons/app/bsky/feed/searchPosts.json
9. **S9** — Bluesky `app.bsky.feed.defs` Lexicon at `f5b411d0dd998820dd363b6cf77f24be061cbd56`: https://raw.githubusercontent.com/bluesky-social/atproto/f5b411d0dd998820dd363b6cf77f24be061cbd56/lexicons/app/bsky/feed/defs.json
10. **S10** — Mastodon Status entity: https://docs.joinmastodon.org/entities/Status/
11. **S11** — Mastodon status methods/context: https://docs.joinmastodon.org/methods/statuses/
12. **S12** — Discourse OpenAPI at `dfcfbf25e603e08ac15645d163a1342604c1976c`: https://github.com/discourse/discourse_api_docs/blob/dfcfbf25e603e08ac15645d163a1342604c1976c/openapi.yml
13. **S13** — Stack Exchange API v2.3 `/questions` contract and filter surface: https://api.stackexchange.com/docs/questions
14. **S14** — Stack Exchange API v2.3 throttles: https://api.stackexchange.com/docs/throttle

## Verification against ticket completion test

`VERIFIED WITH EXPLICIT GAPS`.

- Official access ladder: present for Reddit, X, Hacker News, Bluesky, Mastodon, Discourse, and Stack Exchange.
- Native identity/date/engagement/thread/pagination: exact where S1–S14 specify it; every pruned or absent contract is an explicit feature gap.
- Public/API-key/session/search-fallback, loss, cost/rate/terms/custody, and no-bypass boundary: present; missing policy/rate artifacts are not inferred.
- Initial versus gated disposition and falsifiers: present in the admission matrix.
- Source oracle: exactly 14 resolvable artifact identities; no citation bundles.
