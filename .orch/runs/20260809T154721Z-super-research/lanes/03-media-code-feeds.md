# Lane 03 — media, code/community, and feeds

- `run`: `20260809T154721Z-super-research`
- `ticket`: `03-media-code-feeds`
- `status`: `complete`
- `verification`: `UNVERIFIED` — the dispatch ticket names no oracle or `oracle_class`; the completion-test audit below is evidence, not an oracle verdict.
- `spec_identity`: SHA-256 `4952B1695DC3296203B74720C65E08616DFEDCB56BDEA09D8CD51090BC3CDB89` (verified before research)
- `claim_cutoff`: `2026-08-09`; correction source S07 rechecked `2026-08-10` without asserting a post-cutoff change
- `source_policy`: official platform documentation, standards, and official project repositories only; no credentials, login, restricted-content access, or live platform mutation
- `bound_used`: 14 retained primary artifact identities; 22 substantive reads; no sibling lane read

## Answer

The initial live set should contain three distinct adapter families:

1. a YouTube Data API adapter for dated discovery, batched video hydration, and bounded public comment threads;
2. a GitHub adapter with both public REST and user-authorized, read-only `gh api`/GraphQL routes for repositories, issues/PRs, discussions, comments, and releases; and
3. a public feed adapter for RSS 2.0, Atom, media enclosures, and Podcast Namespace transcript links.

These families cannot share a “generic popularity” field. YouTube views/likes/comment counts, GitHub comments/upvotes/reactions/stars/download counts, and feed-supplied fields are native, observed-time snapshots with different semantics. RSS/Atom normally supplies neither native engagement nor comment bodies.

No undocumented or scraped YouTube route may enter the live default set: YouTube’s current policy requires documented API access and prohibits API clients from scraping YouTube applications or obtaining scraped YouTube data. The compliant official caption route remains OAuth-gated, so arbitrary public-video transcript coverage is an explicit gap rather than an automatic local-tool fallback.

## Falsifiable subclaims

| ID | Subclaim | Finding | Confidence | Evidence that would flip it |
| --- | --- | --- | --- | --- |
| C1 | YouTube’s official API can enforce a hard publication interval during discovery and preserve native engagement during hydration. | Supported. `search.list` accepts `publishedAfter`/`publishedBefore`, date/view-count/relevance orders and page tokens; the video resource supplies publication semantics plus view, like, and comment counts. | High | Current official reference removing those parameters or statistics. |
| C2 | YouTube’s official API can retrieve a complete, arbitrary public-video transcript without user authorization. | Rejected. Caption track listing and download require OAuth 2.0; download is quota-metered and can return 403 for insufficient permission. | High | A documented public caption-text endpoint for arbitrary public videos. |
| C3 | YouTube comment evidence can be collected cheaply and losslessly with one thread call. | Rejected. Thread listing is cheap and pageable, but embedded replies are not guaranteed complete; reply hydration is conditional work. Recent replies to old top-level threads also defeat a naïve top-level date stop. | High for incompleteness; medium for the recent-reply operational consequence | A documented endpoint that enumerates all comments/replies by reply publication time across a video. |
| C4 | An undocumented or scraped extractor is a compliant default substitute for YouTube caption/comment APIs. | Rejected. YouTube requires documented API access and prohibits scraped YouTube data. | High | Written YouTube permission or a policy change expressly admitting the route. |
| C5 | GitHub exposes stable identities, native dates, comments/engagement, and pagination for the requested code/community objects. | Supported for issues/PR-shaped issues, discussions, and releases. PR merge/review detail needs conditional PR hydration; discussions use GraphQL cursor connections. | High | Current REST/GraphQL schemas removing these objects/fields. |
| C6 | RSS/Atom is a low-custody route for timely items and media/transcript discovery. | Supported, with hard limits. Feeds expose item/entry identity and date candidates plus enclosures; Podcast Namespace can link transcripts. A feed is a publisher-selected snapshot, not a complete archive, comment tree, or engagement API. | High | A portable base-spec archive/comment/engagement mechanism. |

## Platform/content/access matrix

| Family | Discovery | Selected hydration | Exact evidence available | Pagination/date control | Custody, dependency, cost | Required loss/failure labels |
| --- | --- | --- | --- | --- | --- | --- |
| YouTube official API, API-key public-data route | `GET /youtube/v3/search`, `type=video`, `q`, `publishedAfter`, `publishedBefore`, `order=date|relevance|viewCount`, `pageToken`. Current reference states 100 calls/day and one Search Queries bucket unit per call. | `videos.list` by selected IDs; `commentThreads.list` only for selected videos; `comments.list(parentId)` when all replies to a retained top-level comment are required. | Video ID/channel ID, title/description, `snippet.publishedAt`, duration/caption availability, region restrictions, and native `viewCount`, `likeCount`, `commentCount`. Comment ID, author channel, parent ID, text representation, `likeCount`, `publishedAt`, `updatedAt`. | Search has hard RFC 3339 interval parameters and page tokens. Comment threads have `order=time|relevance`, max 100 and `nextPageToken`; time order supports bounded top-level traversal but not proof that old threads lack recent replies. | Google sees the request; API key stays outside artifacts. Discovery is the scarce call; video/comment hydration is selected work. Quotas are separate typed budget failures, never silently retried through scraping. | `quota_exhausted`, `comments_disabled`, `forbidden`, `not_found`, `safe_search_applied`, `reply_set_partial`, `caption_unavailable`, `published_at_semantics`, `engagement_observed_at`. ([S01](https://developers.google.com/youtube/v3/docs/search/list), [S02](https://developers.google.com/youtube/v3/docs/videos), [S03](https://developers.google.com/youtube/v3/docs/commentThreads/list)) |
| YouTube official caption route, OAuth | `captions.list(videoId)` after a video is selected. | `captions.download(id, tfmt?, tlang?)`; preserve whether translation was requested. | Caption-track identity and timed-text bytes in the selected format; the implementation guide documents video ID, language, draft visibility, explicit format conversion, and machine-translated language selection. | No discovery role and no cross-video pagination advantage. | OAuth 2.0 user authorization; caption listing and download are quota-metered authorized-data work with explicit retention policy. The retained source does not establish arbitrary-public-video permission. | `auth_required`, `insufficient_permission`, `caption_not_found`, `conversion_failed`, `machine_translated`, `authorized_data`, `no_public_transcript_route`. ([S05](https://developers.google.com/youtube/v3/guides/implementation/captions), [S06](https://developers.google.com/youtube/terms/developer-policies)) |
| GitHub repository metadata, public REST | Exact read contract: `GET /repos/{owner}/{repo}` with `Accept: application/vnd.github+json` and a pinned API-version header. Public repositories require no auth; private metadata uses a read credential. | This call is the repository root hydration before issues, discussions, releases, or code-specific follow-ups. Forks carry `parent` and ultimate `source` objects. | Repository database/node identity, `name`, `full_name`, owner, canonical/API URLs, description/homepage, private/visibility/fork flags, parent/source lineage, language, default branch, topics, license, feature flags, archived/disabled state, created/updated/pushed times, and native `stargazers_count`, `forks_count`, `open_issues_count`. | Single-object lookup has no pagination. Organization/user repository listings are separately pageable and can sort by created/updated/pushed/full name; they are not required when owner/repo is already resolved. | Public route has no secret; metadata-read token is required for private access. Counters and dates are snapshots observed at acquisition, and permission-only fields may be absent. | `repository_not_found`, `private_or_forbidden`, `redirected`, `metadata_permission_partial`, `fork_lineage_partial`, `repository_counter_snapshot`, `code_contents_not_hydrated`. ([S07](https://docs.github.com/en/rest/repos/repos)) |
| GitHub issues/PRs/releases, public REST | Repository issues endpoint with `state`, labels, `sort=created|updated|comments`, `direction`, `since`, page/per-page. The response can include PRs; `pull_request` distinguishes them. Releases are listed separately. | Follow `comments_url` only for retained issues; follow `pull_request.url` when merge/review-specific evidence is needed; hydrate retained releases/assets. | Issue/PR number and node identity, URLs, title/body representations, author, state, labels, created/updated/closed times, comment count and PR marker. Releases expose tag/target, body, draft/prerelease/immutable flags, created/published times, discussion URL, asset digest/size/download count. | Issues support updated-time boundary, sort and max 100/page. Releases support max 100/page but the retained source documents no hard publication interval; cap and label truncation. | Public resources can be requested without auth; the remote sees IP. Direct HTTPS avoids local CLI custody but must own GitHub API version headers, Link pagination, rate headers, and response caps. | `rate_limited`, `secondary_rate_limited`, `target_not_found`, `private_or_forbidden`, `page_partial`, `pr_detail_not_hydrated`, `review_comments_not_hydrated`, `release_window_truncated`. ([S08](https://docs.github.com/en/rest/issues/issues), [S10](https://docs.github.com/en/rest/releases/releases)) |
| GitHub GraphQL discussions | Repository discussions ordered by created/updated time; cursor connection. | Retained discussions’ comments and threaded replies, each as its own cursor connection; reactions only on demand. | Discussion node ID/number/url, author/category/body, created/published/updated/edited/closed times, answer and answer-chosen time, upvote count, reaction groups. Comment ID, author/body, `replyTo`, replies, publication/edit/deletion/minimization state, upvotes/reactions. | `first/after` or `last/before`, `pageInfo`, and total counts. Nested comment/reply cursors must be independent lineage, not flattened into one page token. | GitHub GraphQL credential required. Query complexity and nested page counts are cost; select only fields required by the evidence model. | `auth_required`, `graphql_errors`, `partial_data`, `cursor_invalid`, `field_forbidden`, `comment_connection_partial`, `reply_connection_partial`. ([S09](https://docs.github.com/en/graphql/reference/discussions)) |
| GitHub official CLI, user-authorized read-only route | `gh api` makes authenticated REST v3 or GraphQL v4 requests. | Same API endpoints through stdout; `--jq` can reduce payload, `--cache` can avoid repeat calls, and `--paginate` follows all pages. | Same upstream schema plus process exit/status and optional response headers. | REST pagination is automatic; GraphQL pagination requires `$endCursor` and `pageInfo{hasNextPage,endCursor}`. `--paginate` fetches all pages, so a custom page loop is preferable when an early date stop is valid. | Official local executable and existing `gh` credential store. The core passes an argv array, forces `--method GET`, captures stdout/stderr separately, and never invokes mutation-oriented subcommands. Secrets never enter argv, manifests, or evidence. | `cli_absent`, `not_authenticated`, `wrong_host`, `permission_denied`, `rate_limited`, `nonzero_exit`, `malformed_json`, `partial_page`. ([S11](https://cli.github.com/manual/gh_api)) |
| RSS 2.0 public feed | Fetch an explicit feed URL. Channel `ttl`, `skipHours`, `skipDays`, `pubDate`, and `lastBuildDate` are freshness hints, not hard guarantees. | Hydrate only retained item links, comment-page URLs, enclosure URLs, or transcript URLs through separately admitted adapters. | Channel title/link/description; item title/description, author, categories, `guid`, link, `pubDate`, source, comments-page URL, and enclosure URL/length/MIME type. Every item field is optional except that title or description must exist. | Base RSS is one current document with any number of items; it defines no cursor or archive completeness. `guid` is arbitrary text and only conditionally a permalink. | No credential; one public GET plus selected follow-ups. Parser, XML limits, redirect/SSRF policy, byte caps, and observation time belong to the adapter. | `malformed_xml`, `oversize`, `unsafe_redirect`, `invalid_date`, `date_missing`, `guid_missing`, `snapshot_only`, `comments_url_only`, `no_native_engagement`. ([S12](https://www.rssboard.org/rss-specification)) |
| Atom public feed | Fetch an explicit Atom feed URL; use feed `id`, self link and `updated`. | Hydrate selected `alternate`, `related`, `enclosure`, or content source links. | Required feed ID/title/updated; required entry ID/title/updated, author inherited by rules, optional published/content/summary/source, and typed link relations. Atom IDs are permanent IRIs and revisions retain the same ID. | Base Atom is a document snapshot; RFC 4287 defines no archive cursor. `published` is initial creation/availability; `updated` is the publisher-significant modification time, not a publication substitute. | Same public-GET custody and XML defenses as RSS. | `published_missing`, `updated_is_not_published`, `id_collision_across_publishers`, `snapshot_only`, `extension_unrecognized`, `no_native_engagement`. ([S13](https://www.rfc-editor.org/rfc/rfc4287.html)) |
| Podcast transcript extension over RSS | Discover `<podcast:transcript>` on retained RSS items. | Fetch the selected transcript URL only after MIME/language/size policy and research relevance pass. | Required transcript URL and MIME type; optional language; `rel="captions"` asserts time codes in some form. Multiple formats/languages are allowed. Media remains linked by RSS enclosure rather than downloaded by default. | Inherits the parent feed’s snapshot boundary; no transcript-history cursor. | One additional public fetch per selected transcript. Preserve upstream URL/type/language/rel and byte/model-work budget; the transcript is acquired content, not proof of episode claims. | `transcript_link_only`, `unsupported_mime`, `language_unknown`, `caption_timing_unknown`, `transcript_fetch_failed`, `transcript_oversize`. ([S14](https://github.com/Podcastindex-org/podcast-namespace/blob/c0ff5caa3729610362ee93f8034454fa41f3c493/docs/tags/transcript.md)) |

## Exact evidence mappings and merge boundaries

### Media

- `media_item.platform_item_id` is the YouTube video ID or the target adapter’s documented stable ID; never a normalized title.
- `media_item.published_at` maps to YouTube `snippet.publishedAt` with the source’s private/unlisted exceptions preserved. `observed_at` is always separate. ([S02](https://developers.google.com/youtube/v3/docs/videos))
- `engagement_snapshot.metrics` retains native names and values: `youtube.viewCount`, `youtube.likeCount`, `youtube.commentCount`; record `observed_at` and warnings. Shorts view-count semantics changed in 2025, so metric name alone does not make cross-era counts comparable. ([S02](https://developers.google.com/youtube/v3/docs/videos))
- `comment.platform_comment_id`, `thread_id`, `parent_id`, author channel identity, body representation, `published_at`, `updated_at`, and native `likeCount` stay separate. A thread response that omitted replies carries `reply_set_partial=true`; `totalReplyCount`/embedded replies must not be mistaken for a complete tree. ([S03](https://developers.google.com/youtube/v3/docs/commentThreads/list), [S04](https://developers.google.com/youtube/v3/docs/comments))
- A caption artifact preserves track ID, video ID, requested format/language, whether translation was requested, authorization class, checksum/byte count, and segment timing. Generated or translated caption text is labeled; it is not merged with creator-authored description text. ([S05](https://developers.google.com/youtube/v3/guides/implementation/captions))

### Code/community

- Repository identity is `host + owner + repo` plus returned database/node identity. Preserve owner, canonical/API URLs, description/homepage, private/visibility/fork flags, `parent`/ultimate `source`, language/default branch/topics/license, feature and archive/disabled state, `created_at`/`updated_at`/`pushed_at`, and native stargazer/fork/open-issue counters. Forks remain separate evidence nodes linked to parent/source; equal names or topics never merge them. ([S07](https://docs.github.com/en/rest/repos/repos))
- Repository `updated_at` is metadata activity, `pushed_at` is a repository push timestamp, and neither proves a release, merged PR, commit-level change, or file content. Repository counters are observed snapshots. `GET /repos/{owner}/{repo}` therefore establishes repository identity/context only; code/file/tree content requires a separately admitted contents or Git route and is `code_contents_not_hydrated` in this packet. ([S07](https://docs.github.com/en/rest/repos/repos))
- Issue/PR identity is repository identity plus number/node ID. The issue endpoint’s `pull_request` key is a kind discriminator, not a second item; conditional PR hydration enriches the same evidence node. ([S08](https://docs.github.com/en/rest/issues/issues))
- Issue `created_at`, `updated_at`, `closed_at`, comment count and the observation time remain distinct. `sort=comments` is a within-GitHub attention view; it is not claim confidence. `since` is an update boundary, not a creation boundary. ([S08](https://docs.github.com/en/rest/issues/issues))
- Discussion and discussion-comment node IDs remain distinct from issue IDs. Preserve `replyTo`, answer state, published/updated/edited/deleted/minimized times, native upvotes and reaction groups. Nested cursor lineage is `(discussion_cursor, comment_cursor, reply_cursor)`. ([S09](https://docs.github.com/en/graphql/reference/discussions))
- Release identity is repository plus release/node ID and tag. `created_at` and `published_at` are separate; asset `download_count` is an asset-specific observed snapshot, not repository or release authority. ([S10](https://docs.github.com/en/rest/releases/releases))

### Feeds/news

- RSS dedupe key preference is `(feed canonical URL, guid raw)`; if GUID is absent, retain a declared fallback key and `identity_weak=true`. Never globally merge equal GUID strings because the specification delegates uniqueness to the source. ([S12](https://www.rssboard.org/rss-specification))
- Atom dedupe key is `(publisher/feed identity, atom:id raw)`. RFC 4287 warns about spoofing an ID from another feed, so identical IDs from different publishers do not establish identity. ([S13](https://www.rfc-editor.org/rfc/rfc4287.html))
- Store raw and parsed date values. RSS `pubDate`, Atom `published`, Atom `updated`, feed build/update time, HTTP observation time, and downstream page publication time are separate candidates with separate confidence.
- RSS `<comments>` is only a locator for a comments page; it is not comment content or engagement. Enclosures and podcast transcript tags are descriptors until separately fetched. ([S12](https://www.rssboard.org/rss-specification), [S14](https://github.com/Podcastindex-org/podcast-namespace/blob/c0ff5caa3729610362ee93f8034454fa41f3c493/docs/tags/transcript.md))

## Read-only argv-array routes

These are protocol shapes, not implementation:

```text
["gh", "api", "--method", "GET",
 "repos/{owner}/{repo}"]

["gh", "api", "--method", "GET",
 "repos/{owner}/{repo}/issues",
 "-f", "state=all", "-f", "sort=updated", "-f", "direction=desc",
 "-f", "since=<RFC3339>", "-f", "per_page=100", "--paginate"]

["gh", "api", "graphql",
 "-F", "owner=<owner>", "-F", "name=<repo>", "-f", "query=<read-only-query>"]
```

Because any `-f` parameter otherwise changes `gh api`’s default method to POST, `--method GET` is mandatory for REST reads. GraphQL queries are statically reviewed to exclude `mutation`; variables are separate argv entries. `--paginate` is admitted only when the bounded result is intentionally complete—otherwise the adapter owns one cursor request at a time and can stop at the hard interval. ([S11](https://cli.github.com/manual/gh_api))

No local-media extractor argv route is admitted by this packet. A successor may admit one for a non-YouTube target only after target-specific authority, dependency, schema, and custody evidence passes feature admission; YouTube API failure never authorizes a scraped fallback. ([S06](https://developers.google.com/youtube/terms/developer-policies))

## Efficiency implications and falsifiers

| Change | Work avoided | Necessary condition | Falsifier fixture |
| --- | --- | --- | --- |
| YouTube search first, batch video hydration second | Video-stat calls and payload for rejected results; transcript/comment work for unselected videos | Search result IDs are sufficient for relevance/date preselection | A fixture where the title/snippet omits the only relevance-bearing evidence and hydration changes selection materially. |
| Apply `publishedAfter`/`publishedBefore` and `order=date` | Pages outside the requested interval and local stale filtering | The scenario asks for publication recency, not recommendation rank | An edited old video that the scenario requires because the edit, not publication, is recent. |
| Hydrate comments only for selected videos and replies only for selected top-level comments | Comment pages, content bytes, and model tokens | The research question does not require exhaustive reply coverage | A recent, decisive reply under an old top-level thread; this must produce `recent_reply_coverage_unknown`, not silent success. |
| GitHub issues `sort=updated&since=` before comment/PR hydration | Unchanged issues and most comment bodies | Update time captures the relevant activity window | A required PR review event not reflected in the retained issue update view; conditional PR/review hydration must catch it. |
| GitHub `--jq`/GraphQL field projection | Response bytes, parse state, and downstream model tokens | Excluded fields cannot affect admission or claims | A fixture where an omitted answer/reaction/edit/deletion field changes the evidence interpretation. |
| Feed parse before page/enclosure/transcript fetch | Page/media bytes and model work for stale/unselected entries | Feed metadata dates and summaries are adequate for selection | A feed with missing/wrong dates or a misleading summary; selected-page fallback must be allowed and loss-labeled. |
| Request-local dedupe by platform identity before hydration | Duplicate API/page/transcript calls | Identity is strong and publisher-scoped | Same Atom ID from different publishers or RSS GUID collision; the wrong-merge fixture must remain separate. |

## Adapter protocol implications

Every adapter in this lane needs the following contract behavior:

1. `discover(request, budget) -> page`: hard requested/applied interval, deterministic requested native order, items, cursor/page lineage, upstream identity/version, call cost, and warnings.
2. `hydrate(selection, features, budget) -> partial result`: conditional features (`metadata`, `comments`, `replies`, `captions`, `release_assets`, `discussion_reactions`, `page`, `transcript`) with per-feature call/content caps.
3. Separate `published_at`, `updated_at`, `observed_at`, and `engagement_observed_at`; preserve raw dates and date confidence.
4. Preserve native metric names and scope. No cross-platform score normalization and no popularity-to-confidence conversion.
5. Typed failure at item, page, and feature granularity. A caption 403, disabled YouTube comments, one failed GitHub nested cursor, or one malformed feed item does not erase already acquired evidence.
6. Authority classes are explicit: `public_http`, `api_key`, `oauth_user`, `local_official_cli`, and `local_third_party_tool`. Secrets and browser/session data never enter requests serialized to evidence.
7. Fallback is preauthorized by family and loss-labeled. Direct public GitHub REST may fall back to authorized `gh api` only if allowed; a YouTube API failure never falls back to scraped YouTube data.
8. All CLI execution is argv-array only, has an executable allowlist, fixed read-only subcommand/method, timeout/stdout/stderr/byte caps, clean temporary directory, and no shell/config/plugin/exec expansion.
9. Feed parsing disables external entities, applies decompressed-byte/item/depth limits, validates redirects and resolved targets, and treats all body/summary/transcript/comment text as untrusted acquired content.

## Custody and failure comparison

| Route | Secret/session custody | Local dependency | Upstream-visible data | Dominant cost | Dominant failures |
| --- | --- | --- | --- | --- | --- |
| Public RSS/Atom/transcript HTTP | None | HTTP/XML parser | Request URL, requester IP/headers | Fetch bytes, selected page/transcript model work | malformed/oversize XML, stale snapshot, bad date, SSRF/redirect, missing item |
| YouTube API key | API key outside artifact | HTTP client | Query, project identity | Search-call bucket, core quota, payload | quota, key restriction, filtering, disabled comments, target/schema change |
| YouTube OAuth captions | OAuth token outside artifact; authorized data scoped to authorizing user | OAuth-capable client | Video/track request and user authorization | Quota-metered caption list/download plus transcript bytes/model work | consent/auth, permission, unavailable track, conversion |
| Public GitHub REST | None for public objects | HTTP client | Query, requester IP | API requests/pages, comment bodies | rate/secondary limit, 404, pagination, schema/version |
| Authorized `gh api` | Existing `gh` credential store, not copied | Official `gh` executable | Same API request and authenticated identity | process startup, API requests/pages | CLI absent/auth host mismatch, permission/rate, nonzero exit, partial JSON |

## Contradictions and dominance limits

1. **Mechanism versus permission:** a mechanism nomination never establishes authority. YouTube requires documented API access and prohibits API clients from scraping YouTube applications or obtaining scraped YouTube data; no scraped fallback is admitted. ([S06](https://developers.google.com/youtube/terms/developer-policies))
2. **Caption availability versus caption access:** a video resource can indicate captions, but official caption track listing/download requires OAuth. `caption_available=true` must not imply `transcript_retrievable=true`. ([S02](https://developers.google.com/youtube/v3/docs/videos), [S05](https://developers.google.com/youtube/v3/guides/implementation/captions))
3. **Thread count versus complete tree:** a YouTube top-level thread/listing and a GitHub issue comment count are discovery evidence, not proof that comment bodies/replies/review comments were hydrated.
4. **Freshness versus publication:** Atom requires `updated` but makes `published` optional; RSS item `pubDate` is optional. Neither an observation time nor a build/update time may be silently promoted to publication time. ([S12](https://www.rssboard.org/rss-specification), [S13](https://www.rfc-editor.org/rfc/rfc4287.html))
5. **Attention versus authority:** YouTube views/likes, GitHub comments/upvotes/reactions/downloads, and feed placement may support deterministic within-source attention views only. They do not establish factual authority or independence.

## Probe dispositions, dead ends, and gaps

### Non-retained probes

- Agent Reach at commit `1221ecd0c3e0502ee37406f03543bedf7503f2c7` and Last30Days at commit `1004324ad35a3ba656e6df0faabd54749e398455` confirmed why this lane must test local media mechanisms, `gh`, feeds, and transcripts. They were not retained as platform-capability/permission evidence because project claims cannot establish upstream schema or authority.
- The general YouTube API Services Terms and API root were redundant after retaining the narrower method references and developer policy.
- GitHub pull-request, issue-comment, and rate-limit pages were probed but not retained within the 14-source bound. The issue schema’s PR marker/link and comment URL establish the conditional hydration boundary, but exact PR review-thread and mutable numeric-rate semantics require a successor-spec source refresh.

### Dead ends / explicit gaps

1. No compliant official route retained here supplies transcripts for arbitrary public YouTube videos. OAuth caption access is gated; scraped extraction is not a default-compliant fallback.
2. YouTube comment traversal cannot prove coverage of recent replies to old top-level threads without potentially unbounded parent-by-parent hydration. The adapter must expose the missing-reply coverage dimension.
3. RSS 2.0 and Atom base documents do not define portable archive pagination. Feed-window completeness is unknowable when publishers truncate snapshots.
4. RSS `<comments>` is a page URL only; feed-native comment bodies, votes, views, and reply trees are absent unless a documented extension or separately admitted page/platform adapter supplies them.
5. Conditional HTTP validators, WebSub/rssCloud operations, Atom archive pagination extensions, and HTML feed autodiscovery were not fully sourced within this lane’s bound. Preserve response validators if supplied, but do not promise push or archive coverage from this packet.
6. Exact GitHub PR review-comment/review-thread fields and merge-velocity formulas need a focused successor read. Until then, `pr_detail_not_hydrated` and `review_comments_not_hydrated` are required loss labels.
7. Social-video and regional-video platforms are outside this owning lane; no claim is made about their APIs, sessions, transcripts, or engagement.
8. No live credentialed/API call was permitted, so rate/auth/caption behavior is documentation-backed, not locally exercised. Only successor implementation fixtures can prove argv isolation, schema parsers, typed failures, partial preservation, and cost counters.

## Completion-test audit

1. **Platform/content/access matrix:** present for YouTube, explicit local-media non-admission, GitHub repository/issues/PRs/discussions/releases over REST/GraphQL/CLI, RSS, Atom, and podcast transcript links with current official citations.
2. **Exact fields and boundaries:** present for repository identity/context/counters/dates/fork lineage, media metadata/engagement, comments, caption access, issues/PR markers, discussions/replies, releases/assets, and feed dates/identity/enclosures/transcript descriptors; code contents and omitted review-thread detail are explicit.
3. **API/feed/CLI comparison:** dependency, custody, failures, and operating-cost drivers are tabulated; read-only argv shapes are specified.
4. **Protocol implications and gaps:** explicit, including no scraped YouTube fallback, conditional hydration, cursor lineage, native metric namespaces, and partial-failure preservation.

Because the ticket supplied no named oracle with `oracle_class`, this audit does not change `verification: UNVERIFIED`.

## Retained primary sources (14)

1. **S01 — YouTube Data API, `search.list`**, current page last updated 2026-06-01/2026 API surface, accessed 2026-08-09: <https://developers.google.com/youtube/v3/docs/search/list>
2. **S02 — YouTube Data API, video resource**, accessed 2026-08-09: <https://developers.google.com/youtube/v3/docs/videos>
3. **S03 — YouTube Data API, `commentThreads.list`**, accessed 2026-08-09: <https://developers.google.com/youtube/v3/docs/commentThreads/list>
4. **S04 — YouTube Data API, comment resource**, accessed 2026-08-09: <https://developers.google.com/youtube/v3/docs/comments>
5. **S05 — YouTube Data API, caption implementation guide**, accessed 2026-08-09: <https://developers.google.com/youtube/v3/guides/implementation/captions>
6. **S06 — YouTube API Services Developer Policies**, current policy accessed 2026-08-09: <https://developers.google.com/youtube/terms/developer-policies>
7. **S07 — GitHub REST API, repositories**, rechecked 2026-08-10 for claims at the 2026-08-09 cutoff: <https://docs.github.com/en/rest/repos/repos>
8. **S08 — GitHub REST API, issues**, accessed 2026-08-09: <https://docs.github.com/en/rest/issues/issues>
9. **S09 — GitHub GraphQL API, discussions schema**, accessed 2026-08-09: <https://docs.github.com/en/graphql/reference/discussions>
10. **S10 — GitHub REST API, releases**, accessed 2026-08-09: <https://docs.github.com/en/rest/releases/releases>
11. **S11 — GitHub CLI manual, `gh api`**, accessed 2026-08-09: <https://cli.github.com/manual/gh_api>
12. **S12 — RSS Advisory Board, RSS 2.0 Specification v2.0.11**, stable current specification, accessed 2026-08-09: <https://www.rssboard.org/rss-specification>
13. **S13 — IETF RFC 4287, Atom Syndication Format**, standards-track primary specification, accessed 2026-08-09: <https://www.rfc-editor.org/rfc/rfc4287.html>
14. **S14 — Podcast Namespace transcript tag**, pinned commit `c0ff5caa3729610362ee93f8034454fa41f3c493`, accessed 2026-08-09: <https://github.com/Podcastindex-org/podcast-namespace/blob/c0ff5caa3729610362ee93f8034454fa41f3c493/docs/tags/transcript.md>
