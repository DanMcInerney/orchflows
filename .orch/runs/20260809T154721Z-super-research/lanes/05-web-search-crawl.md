# Lane 05: web search, news, page fetch, and crawl

- `run`: `20260809T154721Z-super-research`
- `ticket`: `05-web-search-crawl`
- `status`: `complete`
- `as_of`: `2026-08-09`
- `spec_sha256`: `4952B1695DC3296203B74720C65E08616DFEDCB56BDEA09D8CD51090BC3CDB89`
- `question`: Which current search-index, news, page-hydration, site-expansion, and extraction mechanisms belong beside platform-native adapters, and what do their date, cost, custody, failure, comment, and transcript limits require?
- `bound_used`: 14 retained primary sources; substantive-read bound respected; no credentialed call, login, or target fetch.

## Verdict

No retained mechanism is a universal winner. The implementable shape is a costed access ladder: minimal index discovery; request-local canonical-URL dedupe; hydration only for selected pages; bounded site expansion only when the question needs site coverage; and platform-native adapters whenever comments, parent/child identity, engagement, moderation state, or captions are required. Search-index material is discovery evidence, not a substitute for a native thread or transcript.

The cheapest compliant family depends on the known state, not claimed retrieval quality. A known public URL should take a local, policy-checked fetch/extract route first; a small public-page workload may use Jina Reader's no-key tier; an already-operated SearXNG or Crawl4AI deployment avoids a hosted per-call fee but still incurs compute, maintenance, and upstream obligations. Among comparable hosted discovery calls, current list prices can be computed, but they do not establish quality superiority. Every fallback must carry explicit loss labels.

## Same-dimension primary-source matrix

All costs are public list terms observed on 2026-08-09, excluding tax and operator compute. “Hosted custody” means the query, target URL, or fetched content crosses to that provider; it does not assert an unreviewed retention duration.

| Mechanism | Discovery and date controls | Fetch, crawl, and returned structure | Usage and cash cost | Custody and failure contract | Native comments/transcripts |
| --- | --- | --- | --- | --- | --- |
| **Brave Search API** | Independent hosted web index; Web Search returns web and optional news, discussions, video and other result families. `freshness` accepts `pd`, `pw`, `pm`, `py`, or `YYYY-MM-DDtoYYYY-MM-DD`; the API defines page age as the most relevant reported date, such as published or modified. `count` is 1–20 for web results, `offset` 0–9, and pages may overlap. [S1] | Structured JSON result cards and up to five extra snippets; LLM Context supplies extracted grounding snippets, but there is no arbitrary-URL fetch, site map, or crawl contract in the retained surface. [S1][S2] | Search is **$5/1,000 requests**, includes $5 monthly credits, and lists 50 requests/s. [S2] | API-key hosted custody. Current public plans do not automatically grant storage rights; Brave says storage needs a plan that explicitly grants them. Input, auth, rate, and server failures must remain distinct; pagination overlap is a documented partial/duplication hazard. [S1][S2] | `discussions` and video result objects are discovery clusters/metadata, not complete native comment trees or captions. No parent IDs, moderation/deletion state, vote snapshots, or transcript text contract is documented. |
| **Exa Search + Contents** | `startPublishedDate` and `endPublishedDate` accept ISO-8601 boundaries; `publishedDate` may be null. Critical drift: `startCrawlDate` and `endCrawlDate` are now deprecated, ignored, and must not be treated as recency enforcement. Public searches return 1–100 results; company/people categories reject several filters with 400. [S3] | One search call can request page `text`, query-relevant `highlights`, LLM `summary`, links, and selected `subpages`; freshness can be controlled with content `maxAgeHours` (`0` live-crawl, `-1` never live-crawl). `outputSchema` is generated synthesis and must remain an acquired artifact, not primary page evidence. [S3] | Search costs **$7/1,000 requests including up to 10 results**, plus **$1/1,000 requests for each additional result above 10**; requests with more than 25 results are listed as an enterprise capability. Text, highlights, and summaries are each separately **$1/1,000 pages per content type**. The response exposes an estimated `costDollars`, while billing uses counters. [S3][S4] | API-key hosted custody; zero-data-retention is listed as enterprise. Preserve request ID, null dates, unsupported-filter 400s, live-crawl timeout, content miss, and per-feature billed usage. [S3][S4] | Page/subpage content is not a native comment graph or caption endpoint. A visible discussion page may yield prose, but native reply identity, votes, moderation, hidden/deleted replies, and transcript provenance remain missing. |
| **Tavily Search, Extract, Map, Crawl** | Search topics include `general`, `news`, and `finance`; `time_range` is day/week/month/year and `start_date`/`end_date` are `YYYY-MM-DD`, applied to publish **or last-updated** date. Results include title, URL, relevance score, content and optional raw content. [S5] | Search can return parsed page content. Crawl exposes `max_depth` 1–5, `max_breadth` 1–500, a total `limit`, path/domain regex filters, and optional external URLs; it returns markdown/text plus request ID and optional usage. [S6] | 1,000 free credits/month; pay-as-you-go **$0.008/credit**. Basic/advanced search costs 1/2 credits. Basic/advanced extract costs 1/2 credits per five successful URLs. Map costs 1 credit per ten successful pages (2 with instructions); crawl is map plus extraction (official example: ten basic pages = 3 credits). [S7] | API-key hosted custody. Extract returns `failed_results`; crawl/search carry request IDs and usage. Preserve 429 with `retry-after`, timeout, failed URL, partial success, and the fact that automatic search parameters can silently choose the 2-credit advanced mode unless depth is pinned. [S5][S6][S7] | No native reply-tree, engagement-snapshot, moderation, or caption contract. `news` is indexed discovery, and raw page content does not prove complete comments or a platform transcript. |
| **Firecrawl Search, Scrape, Crawl** | Search supports web/images/news, domain filters, and `tbs`: hour/day/week/month/year, custom `cdr` dates, and `sbd:1` date sorting. `limit` is 1–100 per selected source type. [S8] | Search optionally scrapes each result. Scrape returns markdown, HTML/raw HTML, links, images, screenshots, summaries or schema-guided JSON. Crawl exposes sitemap mode, discovery depth, page limit, domain/subdomain/external controls, delay/concurrency, and `ignoreRobotsTxt=false`; ignoring robots is enterprise-gated. [S8][S9][S10] | 1,000 free credits/month; no general pay-per-use plan. Search is 2 credits per ten results; scrape/crawl/map are 1 credit/page. JSON mode and enhanced proxy can increase a scrape to 5 credits; failed requests are normally uncharged, with a documented agent exception. [S11] | Hosted or self-operated surface, but the retained endpoint contract is hosted bearer-key custody. Scrape defaults to a two-day cache (`maxAge=172800000`) and `storeInCache=true`; `storeInCache=false` reduces index/cache persistence, while ZDR is gated. Preserve warning, status code, per-result metadata error, 408/429/5xx, async job ID, cache state, and `creditsUsed`. [S8][S9][S10] | Browser actions can reveal rendered replies but do not create native comment identity, pagination completeness, engagement semantics, or moderation state. Search news/video/page extraction is not a transcript/caption API. |
| **Jina Reader/Search** | `s.jina.ai` returns five search entries in JSON mode, but the current retained contract documents no publication-date or custom recency filter. Therefore it cannot enforce a hard requested interval at discovery. [S12] | `r.jina.ai` hydrates a public URL into text/JSON with title, URL, content and timestamp when available; it supports CSS selection, wait/timeout, token budget, PDFs, and schema/instruction extraction. It caches a repeated URL for five minutes and can bypass cache. It cannot read local files or login-only pages and says it does not evade anti-bot/access controls. [S12] | Reader without a key: **20 RPM** and free basic use; free/paid key: 500 RPM. Search without a key is blocked; free/paid key: 100 RPM and each search starts at 10,000 billed tokens. Exact currency per token was not exposed in the retained page, so dollar comparison is a gap. [S12] | Hosted proxy custody even without an API key; forwarding cookies would expand credential custody and is outside the initial public adapter. Treat cache, token-budget failure, timeout, site block, 429, and unavailable timestamp as typed outcomes. [S12] | Jina explicitly says video summarization is planned; current Reader is not a transcript source. Page extraction has the same native-comment incompleteness as other generic fetchers. |
| **Crawl4AI 0.9.x** | No general web/news index or publication-date search. It starts from caller-supplied URLs and can expand with BFS, DFS, or best-first strategies under depth, domain, URL-pattern, content and score filters. [S13] | Local/in-process browser crawling yields crawl depth plus HTML, links and optional markdown/extraction; streaming and crash recovery are documented. Local schemas can extract visible structures, but are site-specific observations. [S13] | No hosted per-call price is established by the retained docs. Cash cost is operator browser/CPU/memory/network plus any optional model/proxy; it is only “zero vendor fee,” not zero total cost. | Local custody for orchestration and extracted artifacts, with outbound target-site exposure. Preserve robots/policy precheck as a caller requirement, browser/TLS/DNS/HTTP failures, selector/schema mismatch, resource exhaustion, and partial streamed results. The retained 0.9.x deep-crawl page does not establish a complete retention/security contract for a network-exposed service; that is a delivery gate. | It can observe rendered comments or caption text only if present in the page. It supplies no platform-native completeness, stable comment IDs, native engagement, or transcript provenance. |
| **SearXNG** | Self-operated metasearch over configured upstream services/databases, not an independent index. `/` and `/search` accept GET/POST; `time_range` is `day`, `month`, or `year` only when an engine supports it, with `pageno`, language, category and safe-search controls. [S14] | JSON/CSV/RSS output is instance-configured; asking for a disabled format returns 403. It returns aggregated result metadata, not arbitrary page hydration or site crawling. [S14] | No vendor per-call tariff is defined for self-hosting. Cost is operator compute/maintenance plus any upstream API credentials or quotas; public-instance capacity is not a dependable free contract. | Query text is passed to external search services, so self-hosting centralizes local logs/config but does not eliminate upstream custody. Preserve configured-engine identity and each engine error/timeout; do not collapse partial multi-engine results into “complete.” [S14] | Any social/news result is index metadata. No native reply tree, engagement snapshot, or transcript contract follows from aggregation. |

## Atomic findings

### F1 — Date filters are not interchangeable

**Observation (high confidence):** Brave filters a provider-selected relevant page date; Tavily filters publish or update date; Exa filters estimated publication date while its crawl-date fields are now ignored; Firecrawl accepts search-engine `tbs`; SearXNG delegates time support to individual engines; Jina and Crawl4AI do not supply hard discovery-date intervals. [S1][S3][S5][S8][S12][S13][S14]

**Design requirement:** Persist `requested_interval`, `provider_date_filter`, `provider_date_semantics`, `result_date_raw`, `result_date_kind`, `date_confidence`, and `observed_at`. A filter being accepted is not proof that every result has an authoritative publication time. Hydration must re-check page-native dates without overwriting the index date.

**Would flip:** an official contract that guarantees one common, authoritative publication-time definition and complete filter enforcement across these providers.

### F2 — Discovery and hydration must be separate budget decisions

**Observation (high confidence):** Brave can return result cards/snippets without arbitrary fetch; Exa, Tavily, and Firecrawl make page content optional and bill or meter it; Firecrawl and Tavily expose separate site-expansion controls; Crawl4AI starts only after URLs are known. [S1][S3][S5][S6][S8][S9][S13]

**Design requirement:** Default to `discover -> canonicalize/dedupe -> select -> hydrate -> optionally expand`. Request no LLM answer/summary, screenshot, schema extraction, or site crawl until the selection rule requires it. This avoids content bytes and billed page reads for rejected results, avoids duplicate hydration of canonical URLs, and avoids model work on pages never cited.

**Falsifier fixture:** a dated query where minimal snippets cause the selector to reject the only relevant primary source, while integrated full-content search retains it. Failure requires widening discovery, a bounded second index, or selective early hydration—not unconditional full-content retrieval.

### F3 — “Cheapest” is a route family, not a provider ranking

**Observation (high confidence for list terms; no quality claim):** Current hosted unit prices differ and request shapes are not equivalent. Local Crawl4AI/SearXNG remove a hosted per-call fee but transfer compute, maintenance, failure recovery, and target-policy work to the operator. Jina Reader has a small no-key public tier but remains third-party custody. [S2][S4][S7][S11][S12][S13][S14]

**Design requirement:** Choose in this order when capability is sufficient:

1. Known public URL: local policy-checked fetch/extract; escalate to a local browser only for required rendering.
2. Small public hydration with no local browser: Jina Reader no-key, loss/custody labeled.
3. Discovery: an already-authorized local metasearch or one user-supplied hosted key, with an explicit cash/request cap.
4. Site question: map first, then hydrate only selected URLs; never default to a whole-domain crawl.
5. Platform question needing comments, engagement, or captions: native adapter, not a cheaper generic substitute.

This ordering asserts avoided fees/calls, not better retrieval. Compare providers only on a frozen workload with equal date bounds, result counts, content options, and failure accounting.

### F4 — Generic web routes cannot satisfy native discussion or transcript requirements

**Observation (high confidence):** The retained web contracts return result cards, page text, extracted fields, links, and rendered content. None promises a complete platform comment graph with stable item/thread/parent IDs, native metric names, moderation/deletion state, and pagination lineage. Jina explicitly has no current video summarization contract. [S1][S3][S5][S8][S10][S12][S13][S14]

**Design requirement:** A generic route may create `web_page` or `search_result` evidence only. It may not promote visible replies into a complete `comment_tree` or page text into a `transcript` unless a native adapter supplies identity, cursor lineage, and completeness. `discussions`, video results, snippets, and rendered comments remain discovery hints.

## Loss-labeled search-index fallback

Search-index fallback is allowed only after the preferred native or page route returns a typed `auth`, `policy`, `rate`, `target`, `timeout`, or `unavailable` failure and the request preauthorizes fallback. It emits an evidence item with:

```yaml
access_path: search_index_fallback
upstream_identity: <provider + endpoint + request_id when supplied>
canonical_locator: <result URL>
observed_at: <UTC>
content_kind: search_result
date:
  raw: <provider value or null>
  semantics: <published|updated|provider_relevant|unknown>
  confidence: <high|medium|low|unknown>
loss:
  - full_content_not_verified
  - publication_time_not_authoritative   # unless independently verified
  - comments_not_complete
  - native_engagement_unavailable
  - moderation_and_deletion_state_unavailable
  - transcript_or_captions_unavailable
  - pagination_completeness_unknown
warnings:
  - fallback_not_native
```

It may preserve a snippet exactly as provider-returned acquired content, but cannot invent platform IDs, authorship, reply parents, votes, or transcript timing. If the index returns no result, that is `fallback_empty`, not proof the item does not exist.

## Failure and custody requirements

The adapter boundary must preserve, without catch-all flattening:

- `auth_missing`, `auth_invalid`, `quota_exhausted`, `rate_limited(retry_after)`, and `billing_cap`;
- `invalid_filter`, `unsupported_filter`, and `filter_ignored` (required for Exa crawl-date drift);
- `robots_disallowed`, `terms_or_policy_disallowed`, `target_blocked`, `login_required`, `tls`, `dns`, `http_status`, and `timeout`;
- `partial_results`, `failed_url`, `pagination_overlap`, `crawl_truncated`, `schema_mismatch`, `cache_stale`, and `unknown_date`;
- provider `request_id`, billed credits/dollars/tokens, cache state, raw warning, result-page/cursor lineage, and the exact upstream identity;
- custody class: `local`, `hosted_no_key`, `hosted_user_key`, or separately gated `user_session`. Secrets and forwarded cookies never enter manifests or artifacts.

Retries are allowed only for retryable transport/429/5xx outcomes, bounded by the source budget and `retry-after`. A policy, auth, invalid-filter, or target-block failure is not retryable through evasive proxying. Partial successful evidence survives every failure.

## Recommendations to synthesis

1. Admit four separate web adapter capabilities rather than one “web” tool: `discover`, `fetch`, `map`, and `crawl`; advertise optional `structured_extract` separately because it can add model work and cost.
2. Initial live set should include one hosted or approved local index route, one local or hosted page route, and one bounded site-expansion route. Provider choice is configuration/BYOK, not kernel policy.
3. Pin date semantics and budgets in each request. Do not treat Exa crawl-date fields, Jina search, Crawl4AI, or an engine-unsupported SearXNG range as satisfying a hard interval.
4. Use index results to find canonical primary pages, then cite hydrated pages. Preserve result rank as provider attention only; it is not claim confidence or cross-provider agreement.
5. Retain native social/media adapters as mandatory for complete comments, engagement, and transcripts. Generic web routes are complementary discovery/recovery paths.
6. Gate session/cookie forwarding, proxy selection, browser actions, and network-exposed local crawlers behind separate custody/security admission tests. The first public web adapter needs none of them.
7. Benchmark list-price/call avoidance separately from recall and evidence quality. A common dated fixture must compare equal result caps and content depth before any quality statement.

## Contradictions and drift register

- **Exa pricing drift:** the cited official pricing URL no longer supports the previously captured result-band prices. Gate recheck on 2026-08-10 shows `$7/1,000 requests` including up to ten results plus `$1/1,000 requests` for every result above ten, with requests above 25 listed as enterprise. The matrix now follows that current contract while preserving the lane's source access date. [S4]
- **Exa documentation drift:** older indexed documentation text described crawl-date filtering as active; the current exact API reference marks both crawl-date fields deprecated and ignored. This packet follows the current reference and requires `filter_ignored` protection. [S3]
- **Jina access drift:** older launch material described no-key search, while the current Reader pricing/rate table marks no-key `s.jina.ai` blocked and no-key Reader available. This packet follows the current table. [S12]
- **Firecrawl cache/freshness tension:** scrape defaults favor a two-day cache while search exposes recency controls. A fresh discovery result does not guarantee fresh hydrated content unless `maxAge` is explicitly tightened. [S8][S10]
- No independent common-workload evidence was retained that permits retrieval-quality ordering. Vendor quality claims are excluded.

## Dead ends and exclusions

- No additional peer was retained: the probes did not add a required custody, failure, data-shape, or recency mechanism beyond the seven matrix rows within this lane's source bound.
- Google Programmable Search, SerpAPI/Serper-style SERP wrappers, and other hosted scraper wrappers were not retained. Within the bound, they did not add a custody/failure/data-shape mechanism needed beyond an independent index, metasearch, integrated search+fetch, hosted reader, or local crawler.
- Provider-generated research/answer endpoints were not retained as evidence authorities. They are generated acquired artifacts and add model cost; primary discovery/fetch contracts are sufficient for this lane.

## Gaps left by the bound

- No live call tested actual date-filter precision, overlap, latency, blocked-target behavior, or output schemas; only local contract/security/benchmark execution can establish them.
- Jina's current page did not expose a stable currency-per-token value, so only its free/rate/token-meter contract is reported.
- Current public retention durations were not established for Brave, Exa, Tavily, or Jina. Treat all hosted routes as provider custody; require a separate terms/security review before sensitive use.
- Crawl4AI's network-server security and retention posture, SearXNG engine-by-engine legality/credentials, and robots enforcement need delivery-time pinned-source review. This lane supports only a local, policy-checked initial use.
- No generic mechanism proves comment completeness or transcript authenticity. Those remain native-adapter requirements, not web-lane defects to paper over.

## Retained primary sources

1. **S1 — Brave Web Search API reference**, accessed 2026-08-09: <https://api-dashboard.search.brave.com/api-reference/web/search/get>
2. **S2 — Brave Search API pricing, capacity, origin, and storage-rights overview**, accessed 2026-08-09: <https://brave.com/search/api/>
3. **S3 — Exa Search API reference**, accessed 2026-08-09: <https://exa.ai/docs/reference/search>
4. **S4 — Exa API pricing**, accessed 2026-08-09: <https://exa.ai/pricing>
5. **S5 — Tavily Search API reference**, accessed 2026-08-09: <https://docs.tavily.com/documentation/api-reference/endpoint/search>
6. **S6 — Tavily Crawl API reference**, accessed 2026-08-09: <https://docs.tavily.com/documentation/api-reference/endpoint/crawl>
7. **S7 — Tavily credits and pricing**, accessed 2026-08-09: <https://docs.tavily.com/documentation/api-credits>
8. **S8 — Firecrawl Search API reference**, accessed 2026-08-09: <https://docs.firecrawl.dev/api-reference/endpoint/search>
9. **S9 — Firecrawl Crawl API reference**, accessed 2026-08-09: <https://docs.firecrawl.dev/api-reference/endpoint/crawl-post>
10. **S10 — Firecrawl Scrape API reference**, accessed 2026-08-09: <https://docs.firecrawl.dev/api-reference/endpoint/scrape>
11. **S11 — Firecrawl pricing and credit rules**, accessed 2026-08-09: <https://www.firecrawl.dev/pricing>
12. **S12 — Jina Reader/Search current usage, rate, cache, access, and extraction contract**, accessed 2026-08-09: <https://jina.ai/reader/>
13. **S13 — Crawl4AI 0.9.x deep-crawling documentation**, accessed 2026-08-09: <https://docs.crawl4ai.com/core/deep-crawling/>
14. **S14 — SearXNG Search API documentation**, accessed 2026-08-09: <https://docs.searxng.org/dev/search_api.html>

## Oracle check

- **Same-dimension matrix:** PASS — seven required mechanisms are compared on date, discovery/fetch/crawl, structure, usage/cost, custody/failure, and comments/transcripts.
- **Exact contracts:** PASS with declared gaps — mutable list terms and endpoint controls are primary-sourced as of 2026-08-09; unexposed retention and Jina token currency are gaps.
- **Cheapest compliant families without superiority:** PASS — cash/call avoidance is separated from total cost and retrieval quality.
- **Complement and fallback:** PASS — native-adapter boundary and loss-labeled search-index fallback are explicit.
- **Verification:** evidence oracle satisfied by current official source trace; no empirical quality or live-access claim made.
