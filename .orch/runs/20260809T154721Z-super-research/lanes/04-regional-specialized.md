# Lane 04 — regional and specialized platforms

- `run`: `20260809T154721Z-super-research`
- `ticket`: `04-regional-specialized`
- `status`: `complete`
- `executor`: `orch-investigate`
- `spec_sha256`: `4952B1695DC3296203B74720C65E08616DFEDCB56BDEA09D8CD51090BC3CDB89`
- `evidence_cutoff`: `2026-08-09`
- `verification`: `UNVERIFIED` — the dispatch named completion criteria but no lane oracle with `oracle_class`; the completion crosswalk below is a self-audit, not an independent verdict.
- `isolation`: the frozen spec and this ticket only; no sibling lane was read.

## Question and falsifiable subclaims

Which regional or specialized platforms are materially present in the current Agent Reach or Last30Days anchors, what native evidence can each return, and which public/API/local-tool/session/page/search-index routes can be admitted without treating an access workaround as permission?

The lane tested four subclaims:

1. The current pinned anchors, not product popularity or stale search summaries, determine the inventory.
2. An anchor's working route is not automatically a compliant route; platform authorization and custody remain separate facts.
3. Native comments, engagement, and dates are admitted only when an official structured surface or an explicitly authorized account/session surface shows them.
4. A search-index hit or public page is lossy discovery evidence, not counterfeit native platform coverage.

Evidence that would flip a `gap` disposition is current platform documentation authorizing a read-only endpoint or automation mode for the proposed use, with a reproducible response schema and retention/rate terms. Evidence that would flip a `gated` disposition to `core` is a public, unauthenticated official read surface whose terms permit the acquisition pattern.

## Exact inventory boundary

### Retained platforms

The pinned Agent Reach commit materially routes six regional/specialized platforms: **Xiaohongshu/RedNote, Bilibili, V2EX, LinkedIn, Xueqiu, and Xiaoyuzhou Podcast** [S1]. The pinned Last30Days source registry and adapters materially add **TikTok, Polymarket, Stocktwits, Techmeme, Truth Social, Trustpilot, and Pinterest**, while overlapping Xiaohongshu and LinkedIn [S2]. These thirteen unique platforms are the lane inventory.

`Douyin`, `Weibo`, and `WeChat Articles` are **not retained**: none has a current channel or source registration in the pinned anchor commits. `Instagram` and `Threads` are evidenced in Last30Days but are general global social platforms, not regional/specialized; `arXiv`, Digg, jobs aggregators, and DripStack are paper/news/general-provider mechanisms rather than a platform family owned by this lane. This boundary is classificatory, not a claim that those sources are absent from the anchors.

## Access and capability matrix

`Native` means the route exposes platform identities/fields rather than only an indexed snippet. `Core` means admissible without a platform account or user session. A generic web-search adapter may discover any public URL below, but must label `access_path=search_index` and the explicit losses shown here.

| Platform | Native evidence evidenced by anchors or official docs | Admissible route ladder | Dependencies, custody, timeliness, and failure limits | Disposition |
| --- | --- | --- | --- | --- |
| **Polymarket** | Official Gamma search returns event/market/profile objects with IDs, slugs, creation/publication/update/end times, volume/liquidity/open-interest fields and `commentCount`; official comments return bodies, parent IDs, creation/update times and reaction counts. Data/CLOB public reads add trades, activity, prices and price history [S4]. | **Official public structured API**: Gamma `public-search`, events/markets, comments; Data API; public CLOB market-data endpoints. Page and search-index routes are only locator fallbacks. | No key or wallet for Gamma/Data and public CLOB reads. Preserve API family and observation time because prices, volume, open interest, reactions and comments change. Paginate with documented `limit`/`offset`; Cloudflare throttles above endpoint-specific limits. Trading endpoints are unreachable by this research skill. | **CORE** |
| **TikTok** | Research API can query public videos by date/keyword/hashtag/user/region and return video ID, description, creation time, counts for views/likes/comments/shares/favorites, duration and optional voice-to-text. Its comment endpoint returns comment/reply IDs, parent ID, text, create time, like and reply counts [S3]. Last30Days instead uses a third-party API for keyword/hashtag/profile search and transcript enrichment [S2]. | **Official API with project approval**: Research API. Search-index/public-page fallback may retain URL/snippet/date only. Do not substitute the anchor's third-party wrapper as proof of TikTok authorization. | Research eligibility, application approval, client token and `research.data.basic`; 1,000 requests/day and up to 100 records/request. New videos can lag up to 48 hours and archived engagement can lag up to 10 days [S3]. Tokens expire; deleted/private content can shrink pages. | **GATED** |
| **LinkedIn** | Official Community Management surfaces organization/member posts, comments/replies, reactions and social metadata, but permissions and developer review constrain whose data may be read [S5]. Agent Reach uses a logged-in browser-automation MCP for profiles/people/companies/jobs and a page-reader fallback; Last30Days uses third-party, Google-index-derived post search [S1,S2]. | **Official API with OAuth and approved product tier** for authorized organization/member content. **Search-index fallback** may preserve public locator/snippet/date. No automated page hydration without LinkedIn's express crawling permission. | Development/Standard tier review, OAuth scopes, page-role checks, re-consent, API-version churn and storage restrictions. LinkedIn prohibits unauthorized crawling and third-party automation, including indirectly obtained non-official content [S6]. Therefore Agent Reach's MCP/Jina and Last30Days's third-party post search are not admitted as compliant native routes. | **GATED** |
| **V2EX** | Official API 2.0 provides node topics, topic detail, topic replies, member/token/notification reads and page-number pagination [S7]. Agent Reach also calls older public JSON topic/reply/member endpoints without auth [S1]. | **Official API with user-supplied Personal Access Token**. Public page/search-index fallback is discovery-only. Treat the legacy anonymous JSON endpoints as provisional until current official documentation confirms their support/terms. | Bearer PAT held only in process; no manifest/artifact secret. Official default limit is 600 requests/IP/hour and exposes rate headers [S7]. Page through topics/replies and stop at the date boundary when response dates exist. Auth, 429, deleted topic/reply and schema drift remain typed failures. | **GATED** |
| **Xiaohongshu / RedNote** | Agent Reach reports note search/read, feed/user notes, interaction counts, and nested comments through OpenCLI or MCP; Last30Days records note ID, `xsec_token`, note time and like/comment/favorite counts through a logged-in local service [S1,S2]. | Search-index fallback only for public locator/snippet. A user-controlled visible session is a **candidate** gated route, not admitted until platform authorization is established. The official open API material found is commerce/partner inventory and orders, not public note/comment discovery [S8]. | Existing Chrome session or manually exported same-domain cookies; ephemeral `xsec_token`; large headless-browser dependency in one backend. Anchor warns deep requests trigger CAPTCHA and discontinued clients fail. Current `robots.txt` disallows `/` for generic agents [S8]. Do not automate login, bypass CAPTCHA, replay protected tokens outside their returned flow, or infer that user consent overrides platform terms. | **GAP** |
| **Bilibili** | Agent Reach reports search/hot/rank, video detail with view/interaction metadata, audio extraction, and subtitle cues; its prior `yt-dlp` route now fails with HTTP 412 [S1]. No anchor-native comment hydration is evidenced. | Search-index locator and user-opened public page only. Official partner/Open Platform access could become gated if its exact product authorizes the intended reads. The anchor's `bili-cli`, OpenCLI and direct internal-search endpoint are not admitted as authorization. | Local CLI or browser extension; subtitles may require a user session. The official user terms prohibit obtaining platform services/content/data with robots, scripts, spiders or crawlers without prior express written permission [S9]. 412, missing subtitle, region/IP restrictions and schema drift are explicit failures; no evasion or proxy prescription enters the design. | **GAP** |
| **Xueqiu** | Agent Reach reports symbol search, quotes, hot posts and hot stocks through an existing browser session or minimum `xq_a_token` [S1]. The anchor does not establish a public official research API. | Search-index locator only. A platform-approved data license/API would be gated; existing-session/internal-endpoint acquisition is not admitted. | Browser session/cookie custody, quote delay, HTTP 400 ambiguity, and parsing drift. Xueqiu's current `robots.txt` disallows AI/RAG use without express permission and blocks JSON/query/stock paths for generic agents [S10]. Do not store the token or treat a successful browser read as reuse permission. | **GAP** |
| **Xiaoyuzhou Podcast** | Agent Reach accepts an episode URL, obtains audio, and generates an ASR transcript; this is a derived transcript, not a platform-native caption/comment surface [S1]. | Public page/search-index discovery may retain episode URL and visible metadata. Audio retrieval plus transcription is not a platform adapter until platform/content terms are established; user-provided media may be processed only behind separate explicit processor authorization. | `ffmpeg`, an explicit Groq or OpenAI key, audio transfer to the selected processor, and optional second model pass. Preserve processor identity, generated status and cue/time loss. No native comments or engagement are evidenced; missing audio, paywall, processor failure and long-episode cost remain typed. | **GAP for platform acquisition; gated user-provided transcript** |
| **Stocktwits** | Last30Days uses undocumented v2 symbol search/stream URLs and normalizes message IDs, cashtag/symbol, create time, likes, reshares, author followers and tagged sentiment [S2]. | Existing officially approved API clients may be gated. Search-index fallback otherwise. Do not call the anchor's undocumented anonymous endpoints as core. | Stocktwits' official developer page says APIs/docs/terms are under review and new application registration is closed [S11]. Rate/retention guarantees therefore cannot be established from current official docs. Empty/rate-limited responses must remain failures, not “no discussion.” | **GAP for new delivery** |
| **Trustpilot** | Last30Days returns a business identity/domain, TrustScore, review count and Trustpilot-generated summary, but not review-level posts/comments; its local CLI harvests an AWS WAF token with headless Chrome [S2]. | **Official partner/API access** may be gated under an approved plan/integration. Search-index/public business-profile snippets can discover a locator. Reject the WAF-cookie route. | Official pricing exposes API access as an add-on on higher plans and Trustpilot offers partner/review-syndication programs [S12]. The anchor's automatic WAF-token harvest is outside this spec's permitted mechanisms. Review-level dates/text and API retention/rates remain unproved in this lane. | **GATED official API; anchor route rejected** |
| **Truth Social** | Last30Days calls a Mastodon-shaped `/api/v2/search` with a bearer token and maps status URL/date plus favourite/reblog/reply counts [S2]. | Search-index fallback only. A documented Truth Social public or OAuth API could become gated. | The anchor obtains a bearer token from browser developer tools and reports 401, Cloudflare 403, 429 and schema failures [S2]. No current first-party API/terms source within the bound established authorization, token scope, retention or pagination. Token extraction is not an admissible custody plan. | **GAP** |
| **Techmeme** | Last30Days invokes a local CLI against a live archive and returns headline, publication, link and ISO date when parseable; it exposes no native comments or engagement [S2]. | Search-index/page discovery only unless Techmeme documents an authorized feed/API. | Local binary dependency, decades-deep archive, client-side hard date filtering, undated-record fallback and markup/schema drift. Undated hits must carry low date confidence and never be stamped “today.” This is a news/page item, not a social post. | **GAP** |
| **Pinterest** | Last30Days's opt-in third-party adapter maps pin ID/URL, description/media, creator, save and comment counts, and sorts by saves [S2]. | Search-index fallback only in this evidence cut. A future official Pinterest API adapter needs scope-by-scope admission evidence for public discovery and the requested fields. | Third-party API key and provider custody in the anchor; no retained first-party source establishes general keyword search, comments, dates, or reuse terms. Provider success is not platform permission. | **GAP** |

## Required protocol projection

Every adapter above must emit the common provenance envelope:

`platform`, `platform_item_id`, `platform_thread_id`, `parent_item_id`, `canonical_locator`, `author`, `community_or_container`, `content_kind`, `content`, `published_at`, `edited_at`, `observed_at`, `publication_time_confidence`, `engagement_snapshot_at`, `native_metrics`, `cursor_or_page`, `access_class`, `upstream_identity`, `credential_owner`, `warnings`, `partial_failures`, and `explicit_loss`.

Platform projections must keep native names and identities:

| Platform | Identity/thread projection | Native metric/date projection | Mandatory loss/warning fields |
| --- | --- | --- | --- |
| Polymarket | `event.id`, `market.id`, slug, comment ID, `parentCommentID`; trades stay separate from comments | `volume*`, `liquidity*`, `openInterest`, `outcomePrices`, `commentCount`, `reactionCount`, `createdAt/updatedAt/endDate` | changing-price snapshot time; market probability is attention/price evidence, never claim confidence |
| TikTok | video ID; comment ID; `parent_comment_id`; query `search_id` and cursor | `view_count`, `like_count`, `comment_count`, `share_count`, `favorites_count`; video/comment `create_time` | Research archive lag, deleted/private omissions, voice-to-text availability, gated project identity |
| LinkedIn | post/share URN; comment URN and parent; actor/org URN | reactions by native type, comments, reposts/social metadata; created/last-modified time | permission/scope, authorized organization/member boundary, API version, storage restriction; search-index metrics absent |
| V2EX | topic ID, node name, reply ID with topic as parent | topic/reply publication fields and reply count only when returned | PAT access, page lineage, deleted content; legacy-anonymous route warning if ever tested |
| Xiaohongshu | note/feed ID, ephemeral `xsec_token`, comment and parent-comment IDs | `likedCount`, `commentCount`, `collectedCount`, note time | session/token origin, CAPTCHA/partial tree, robots/authorization gap; never persist cookies or `xsec_token` as a secret substitute |
| Bilibili | BV/AV identity, content/CID identity, subtitle track/cue identity | route-returned view/danmaku/reply/favorite/coin/share/like values and publication time, each namespaced | comments unavailable, subtitle provenance, 412/region/session loss, authorization gap |
| Xueqiu | symbol plus post/quote identity only when returned | native quote/post/hot metrics and their observed time, never normalized across platforms | possible quote delay, session scope, AI/RAG prohibition, no admitted API |
| Xiaoyuzhou | episode ID/URL, podcast identity, audio identity, transcript segment/cue | visible published/duration fields; ASR has `generated_at` and processor, not a native post date | generated transcript, processor custody, missing native comments/engagement, content-rights gate |
| Stocktwits | symbol/cashtag, message ID | likes, reshares, followers, tagged sentiment, `created_at` | undocumented endpoint, registration closure, rate/retention unknown |
| Trustpilot | business-unit/domain and review ID only through official API | TrustScore and review count as observed snapshots; review rating/date only when official API returns them | WAF route rejected, plan/partner scope, summary may be generated and must be labeled |
| Truth Social | status ID/URL and reply/root IDs only through an admitted API | favourites/reblogs/replies and `created_at` | token origin/scope unknown, Cloudflare/rate/auth failures, no platform authorization evidence |
| Techmeme | archive result/link and publication | source/headline/date; no native engagement | undated/markup drift, archive recency window, page/news rather than social semantics |
| Pinterest | pin ID/URL and creator/container only through an admitted API | native saves/comments and publication time only when first-party route proves them | current anchor is third-party; comments/date may be absent; no authorization evidence |

Search-index fallback for every row may populate only `canonical_locator`, title/snippet, provider rank, provider-observed time, and a publication time with explicit confidence when the index supplies one. It must set `native_metrics={}`, `comments_state=unavailable`, and `explicit_loss=[index_coverage, native_thread, native_engagement, deletion_state]`. A fetched public page may add visibly rendered fields but cannot upgrade the access class to `native_api`.

## Acquisition consequences

1. **Keep Polymarket as the only unconditional initial adapter from this lane.** One public search call can select event/market IDs; hydrate only selected events, markets and bounded comments. This avoids full-market pagination and comment calls for rejected candidates. Falsifier: a fixture where `public-search` omits a relevant active market that the paginated events endpoint finds.
2. **Implement TikTok, LinkedIn and V2EX as separately enabled credentialed adapters.** Each receives a request-local credential handle, never a secret value in a manifest/artifact. Their feature admission fixtures must prove exact date bounds, cursor lineage, nested comments/replies, metric snapshot time, and typed auth/rate/schema failures. Falsifier: the same public record cannot be reproduced with the documented scope at the pinned API version.
3. **Do not port anchor workarounds.** Reject WAF-cookie harvesting, bearer-token extraction from developer tools, undocumented/internal endpoints, automated login, CAPTCHA handling, or session reuse not independently authorized by platform rules. Their only architectural value is as evidence of demand and failure modes.
4. **Keep discovery separate from hydration.** Generic search can cheaply locate LinkedIn/Bilibili/Xiaohongshu/Xueqiu/Xiaoyuzhou/Stocktwits/Trustpilot/Truth Social/Techmeme/Pinterest URLs. It cannot supply native thread completeness, engagement, edits/deletions, or reliable dates; selection does not authorize hydration.
5. **Never use cross-platform engagement as confidence.** Polymarket price/volume, TikTok views, Xiaohongshu collections, V2EX replies, TrustScore, and Stocktwits likes remain namespaced attention snapshots.

## Findings

### F1 — the anchor platform set is broader than its defensible access set

**Observation (high confidence, current to 2026-08-09):** the pinned anchors materially implement thirteen regional/specialized platforms, but only Polymarket has a current, public, no-auth official structured route established by this lane [S1-S4].

**Judgment:** platform breadth should be represented as `core`, `gated`, and `gap`, never as a single “supported” count. Losing this finding would require current official public read documentation for one or more gap platforms.

### F2 — official gated APIs preserve the highest-value native data

**Observation (high confidence):** TikTok Research API exposes bounded date query, video engagement, voice-to-text, and nested comment identities/metrics; LinkedIn Community Management exposes authorized posts/comments/reactions; V2EX API 2.0 exposes topics and replies under a PAT [S3,S5,S7].

**Judgment:** these adapters are worth a gated delivery because a generic search/page route cannot reconstruct native parents, cursors, metrics, or deletion/private omissions. The finding flips if the APIs remove those fields or the intended user/research class cannot obtain their scopes.

### F3 — user possession of a browser session is not platform authorization

**Observation (high confidence):** Agent Reach relies on existing sessions/cookies for Xiaohongshu, LinkedIn and Xueqiu; Last30Days additionally describes WAF-cookie acquisition for Trustpilot and browser-derived bearer use for Truth Social [S1,S2]. LinkedIn expressly prohibits unauthorized automation/crawling, Bilibili prohibits automated content/data acquisition without written permission, Xiaohongshu disallows generic agents in `robots.txt`, and Xueqiu's `robots.txt` expressly prohibits unpermitted AI/RAG use [S6,S8-S10].

**Judgment:** session adapters require both user authorization and a platform-permitted access pattern. Browser control is a custody class, not a compliance bypass.

### F4 — timeliness is platform-specific and must be executable

**Observation (high confidence):** TikTok's research search may lag new videos by 48 hours and engagement by 10 days [S3]; Polymarket market and comment state changes continuously and exposes public endpoints with distinct rate limits [S4]; V2EX publishes page/rate mechanics [S7]; anchor-only local tools expose additional stale-schema, undated-record, CAPTCHA, 412, Cloudflare and token-expiry failures [S1,S2].

**Judgment:** every record needs both `published_at` and `observed_at`; engagement needs `engagement_snapshot_at`; undated and archived/search-index results cannot satisfy a hard interval silently.

## Contradictions register

| Sources | Disagreement | Resolution |
| --- | --- | --- |
| Agent Reach [S1] vs platform terms/docs [S6,S8-S10] | The anchor presents several browser/CLI routes as usable; platform primary material does not establish permission and sometimes expressly restricts the automation. | Preserve capability as an anchor observation; reject compliance inference. Route remains gap or gated pending authorization. |
| Agent Reach [S1] vs V2EX official docs [S7] | Anchor calls older anonymous JSON endpoints; current official API 2.0 documents PAT-authenticated endpoints. | Prefer documented API 2.0 for the proposed adapter; label legacy anonymous calls provisional. |
| Last30Days [S2] vs Stocktwits [S11] | Anchor describes public anonymous v2 endpoints and an approximate quota; official developer page says APIs/docs/terms are under review and new registration is closed. | No new core adapter; existing approved access can be evaluated separately. |
| Last30Days [S2] vs Trustpilot [S12] | Anchor acquires a WAF token with headless Chrome; Trustpilot offers paid/partner API access. | Reject WAF route; admit only official partner/API route behind an explicit gate. |

## Dead ends

- Bilibili's official Open Platform landing page established that an official developer surface exists but did not, within this lane's read bound, establish public search, comment, subtitle, or general research scopes. It cannot support an adapter claim.
- Xiaohongshu's official open-platform pages found commerce inventory/order APIs, not general public notes/comments/search [S8].
- No retained first-party Truth Social API/terms page established that its Mastodon-shaped search endpoint is a public developer contract; Mastodon documentation would describe a shared software upstream, not Truth Social's authorization.
- No retained first-party Techmeme API/feed contract established permission for the anchor's archive CLI.
- Direct GitHub API URLs were rejected by the browsing tool; current anchor identities were therefore pinned with official Git transport (`git ls-remote`) and content fetched from commit-specific official GitHub URLs.

## Gaps and bound

- No live credentialed call, login, restricted-content access, or platform mutation was performed; therefore runtime schemas for gated routes still need contract fixtures and approved-account tests.
- The bound did not establish official discovery/comment APIs for Xiaohongshu, Bilibili, Xueqiu, Xiaoyuzhou, Truth Social, Techmeme, or Pinterest; those remain gaps rather than negative universal claims that no API exists.
- The bound did not establish Trustpilot review-level API fields, rates, or retention, only the official availability of higher-tier/partner API access.
- The bound did not test geographic availability, account eligibility, moderation/deletion behavior, or payload drift. Platform docs and terms are mutable; admission must pin API version/terms access date and fail closed when they change.
- Search-index fallbacks cannot prove native completeness, comment ordering, engagement freshness, edit/deletion state, or publication time.

## Source register — 12 retained primary-source identities

All mutable pages were accessed 2026-08-09.

1. **[S1] Agent Reach repository, commit `1221ecd0c3e0502ee37406f03543bedf7503f2c7`** — current platform routing, capabilities, dependencies, custody and failures: [SKILL.md](https://github.com/Panniantong/Agent-Reach/blob/1221ecd0c3e0502ee37406f03543bedf7503f2c7/agent_reach/skill/SKILL.md), [README](https://github.com/Panniantong/Agent-Reach/blob/1221ecd0c3e0502ee37406f03543bedf7503f2c7/docs/README_en.md), [social](https://github.com/Panniantong/Agent-Reach/blob/1221ecd0c3e0502ee37406f03543bedf7503f2c7/agent_reach/skill/references/social.md), [career](https://github.com/Panniantong/Agent-Reach/blob/1221ecd0c3e0502ee37406f03543bedf7503f2c7/agent_reach/skill/references/career.md), [video](https://github.com/Panniantong/Agent-Reach/blob/1221ecd0c3e0502ee37406f03543bedf7503f2c7/agent_reach/skill/references/video.md), [finance](https://github.com/Panniantong/Agent-Reach/blob/1221ecd0c3e0502ee37406f03543bedf7503f2c7/agent_reach/skill/references/finance.md).
2. **[S2] Last30Days repository, commit `1004324ad35a3ba656e6df0faabd54749e398455`** — source admission and platform adapter implementations: [pipeline](https://github.com/mvanhorn/last30days-skill/blob/1004324ad35a3ba656e6df0faabd54749e398455/skills/last30days/scripts/lib/pipeline.py), [TikTok](https://github.com/mvanhorn/last30days-skill/blob/1004324ad35a3ba656e6df0faabd54749e398455/skills/last30days/scripts/lib/tiktok.py), [Polymarket](https://github.com/mvanhorn/last30days-skill/blob/1004324ad35a3ba656e6df0faabd54749e398455/skills/last30days/scripts/lib/polymarket.py), [LinkedIn](https://github.com/mvanhorn/last30days-skill/blob/1004324ad35a3ba656e6df0faabd54749e398455/skills/last30days/scripts/lib/linkedin.py), [Xiaohongshu](https://github.com/mvanhorn/last30days-skill/blob/1004324ad35a3ba656e6df0faabd54749e398455/skills/last30days/scripts/lib/xiaohongshu_api.py), [Stocktwits](https://github.com/mvanhorn/last30days-skill/blob/1004324ad35a3ba656e6df0faabd54749e398455/skills/last30days/scripts/lib/stocktwits.py), [Trustpilot](https://github.com/mvanhorn/last30days-skill/blob/1004324ad35a3ba656e6df0faabd54749e398455/skills/last30days/scripts/lib/trustpilot.py), [Truth Social](https://github.com/mvanhorn/last30days-skill/blob/1004324ad35a3ba656e6df0faabd54749e398455/skills/last30days/scripts/lib/truthsocial.py), [Techmeme](https://github.com/mvanhorn/last30days-skill/blob/1004324ad35a3ba656e6df0faabd54749e398455/skills/last30days/scripts/lib/techmeme.py), [Pinterest](https://github.com/mvanhorn/last30days-skill/blob/1004324ad35a3ba656e6df0faabd54749e398455/skills/last30days/scripts/lib/pinterest.py).
3. **[S3] TikTok for Developers Research API documentation** — [video query schema](https://developers.tiktok.com/doc/research-api-specs-query-videos/), [comments](https://developers.tiktok.com/doc/research-api-specs-query-video-comments), [codebook](https://developers.tiktok.com/doc/research-api-codebook), [eligibility/quota/lag FAQ](https://developers.tiktok.com/doc/research-api-faq).
4. **[S4] Polymarket official API documentation** — [API overview/authentication](https://docs.polymarket.com/api-reference/introduction), [public search](https://docs.polymarket.com/api-reference/search/search-markets-events-and-profiles), [comments](https://docs.polymarket.com/api-reference/comments/list-comments), [rate limits](https://docs.polymarket.com/api-reference/rate-limits).
5. **[S5] LinkedIn official Community Management documentation** — [Comments API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/comments-api?view=li-lms-2026-04), [access/migration guide](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/community-management-api-migration-guide?view=li-lms-2026-06).
6. **[S6] LinkedIn legal and automation rules** — [Crawling Terms](https://www.linkedin.com/legal/crawling-terms), [API Terms](https://www.linkedin.com/legal/l/api-terms-of-use), [prohibited software](https://www.linkedin.com/help/linkedin/answer/a1341387/prohibited-software-and-extensions?lang=en).
7. **[S7] V2EX official API 2.0 Beta** — [topics, replies, pagination, PAT and rates](https://www.v2ex.com/help/api).
8. **[S8] Xiaohongshu official surfaces** — [Open Platform scope](https://school.xiaohongshu.com/en/open/quick-start/introduction.html), [robots.txt](https://www.xiaohongshu.com/robots.txt).
9. **[S9] Bilibili Terms of User Service** — [automation/data acquisition restriction](https://www.bilibili.com/blackboard/protocal/activity-1RIGA-C2-.html).
10. **[S10] Xueqiu robots.txt** — [AI/RAG and path restrictions](https://xueqiu.com/robots.txt).
11. **[S11] Stocktwits for Developers** — [API review and registration status](https://api.stocktwits.com/developers).
12. **[S12] Trustpilot official business/partner surfaces** — [pricing and API-access tier](https://business.trustpilot.com/pricing), [partner/review-syndication program](https://uk.business.trustpilot.com/partners).

## Completion crosswalk

| Criterion | Result |
| --- | --- |
| Exact evidenced platform list; no popularity expansion | **Met** — thirteen retained; absent and out-of-family candidates explicitly separated. |
| Primary-source access/capability matrix; native vs inferred/indexed | **Met** — matrix distinguishes official native, anchor observation, page and search-index loss. |
| Custody, session, anti-bot/terms, failure, dependency and timeliness | **Met** — each row carries dependencies and typed limitations; no evasion route is described. |
| Core/gated/gap disposition and protocol fields | **Met** — one core, four gated/gated-partial, eight gaps; common and platform-native projections supplied. |
