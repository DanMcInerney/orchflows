# Lane 06: compliant access and custody

- `run`: `20260809T154721Z-super-research`
- `ticket`: `06-access-custody`
- `status`: `complete`
- `evidence_cutoff`: `2026-08-09`
- `verification`: `UNVERIFIED` — the dispatch ticket names no oracle or `oracle_class`; the packet is shaped for the downstream independent research gate.
- `source_bound`: 14 retained primary authorities; 20 targeted substantive section reads; no credential, login, user session, restricted content, or external mutation used.
- `write_scope`: this lane packet only.

## Answer

The super-research kernel should admit six access classes in a fixed authority ladder, but it must not try them as an ambient cascade. A request first preauthorizes exact route IDs and a fallback order. Each fallback is a new evidence route with its own upstream identity and explicit loss vector; it can reduce fidelity but cannot gain credentials, session visibility, target origins, methods, or retention rights.

“Read-only” is an enforced capability, not a property inferred from public visibility, an API key, an installed CLI, an authenticated browser, or an HTTP `GET`. Every adapter needs both a target allowlist and an operation allowlist. The research surface exposes no write operation, the transport rejects state-changing methods and action endpoints, approved CLIs receive only a fixed argv grammar, and browser/session adapters cannot submit forms, click action controls, export session state, download files, or invoke arbitrary script. This follows orchflows authority attenuation: a child receives only its write scope plus excluded actions, and an excluded action stops rather than silently widening authority [S1].

The first delivery should enable public structured endpoints/feeds, user-supplied API-key routes, approved local read-only CLI routes, compliant uncredentialed page fetch, and search-index discovery. User-authorized browser/session routes should remain separately gated until their provider can prove session-state non-export, origin/method/action enforcement, artifact redaction, and deterministic teardown. A session route is not a fallback for an API denial.

## Decisive contract

### Access ladder

| Rank / access class | Admission and preauthorization | Custody and upstream identity | Rate, terms, retention | Typed stop or loss | Delivery |
| --- | --- | --- | --- | --- | --- |
| A0 `public_structured` | Exact official endpoint or publisher feed, hostname, adapter version, and read endpoint are declared before execution. No credentials. | Identity is `{route_class, adapter_id@version, upstream_service, origin, native_item_id/feed_id, observed_at}`. Preserve Atom `id`, `source`, `published`, and `updated` separately: Atom IDs are permanent identifiers, `published` is an early-life-cycle time, and `updated` means only a publisher-significant modification [S5]. | Publisher terms and advertised quotas still apply; “public” grants no universal retention right. Cache only within the run unless the adapter has an affirmative retention rule. | `policy_unknown`, `rate_limited`, `schema_mismatch`, `source_partial`. A feed lacking comments or engagement records those fields as unavailable, never zero. | First delivery. |
| A1 `user_api_key` | User opts into one official API adapter and supplies a key or OAuth handle out of band. Requested scopes/endpoints must be read-only and minimally sufficient. OAuth BCP requires minimum privilege and audience restriction [S2]; GitHub fine-grained token permissions bound reachable endpoints [S7]. | Secret resolver returns an ephemeral handle directly to the transport. The core never sees or serializes the value. Identity records service/project plus a non-secret credential-slot ID and, when safely returned, the authenticated principal—not a token fingerprint. | One governor per `{upstream_service, project/principal slot}` owns concurrency and budgets. Honor response headers and `Retry-After`; do not rotate credentials or shard projects to evade limits. GitHub exposes remaining/reset headers and directs clients not to retry before reset [S8]. Platform retention overrides local defaults: Reddit requires approved-use retention and deletion when no longer required/at termination [S10]; YouTube commonly requires refresh or deletion within 30 days and deletion after revoked authorization [S11]. | `secret_unavailable`, `scope_insufficient`, `auth_expired`, `auth_identity_mismatch`, `rate_limited`, `terms_gate`, `retention_expired`. No automatic session fallback. | First delivery, adapter-by-adapter. |
| A2 `approved_local_cli` | Exact resolved executable path, version range or digest, upstream host, cwd, minimal environment profile, endpoint grammar, and argv grammar are approved. Invocation is an argv array with `shell=False`; Python recommends an argument sequence and fully qualified executable [S6]. | The CLI may use its own already-authorized credential store, but the core may neither request nor print the credential. Record executable identity, CLI version, selected host, endpoint, method, and local account label if the CLI safely exposes it. | Inherits the upstream API's terms, rate bucket, scope, and retention; a wrapper does not create new permission. GitHub CLI `gh api` is authenticated, defaults to `GET`, but also exposes arbitrary methods, request bodies, headers, verbose output, pagination, and write examples [S9]. Therefore only a fixed read subset is admissible. | `tool_not_approved`, `tool_version_mismatch`, `argv_denied`, `method_denied`, `host_mismatch`, `raw_output_rejected`, then the upstream typed failures. | First delivery only for named, tested CLIs. |
| A3 `user_session_readonly` | Separate explicit user authorization for one origin, purpose, time window, content class, and read-only action grammar. It is never inferred from an existing signed-in browser and never entered by fallback unless the request named it. | Session cookies, local storage, headers, CSRF values, and browser state remain inside the provider. Only normalized evidence leaves it. Playwright warns that saved auth state can contain cookies and headers capable of impersonation [S12]. Identity is `{session_route_id, provider, authorized_origin, account_label_if_visible, observed_at}`; no session-state hash. | Default payload retention is current run only; no cross-run cache. Platform terms and authorized-content deletion rules override. Destroy the isolated context at completion or revocation. | `session_not_authorized`, `origin_denied`, `action_denied`, `session_expired`, `session_state_export_denied`, `authorized_content_retention_denied`. | Gated after first delivery. |
| A4 `page_fetch` | Uncredentialed `GET`/`HEAD` to an exact preauthorized public origin and path policy, after terms and robots evaluation. Robots rules control crawler access but are explicitly not access authorization; successful robots fetches must be honored [S4]. | Record requested URL, redirect chain, final URL/origin, status, media type, validators, and observation time. Content is untrusted data. | Per-origin concurrency, byte/time/redirect ceilings, conditional requests when allowed, and publisher terms. No cookies or ambient browser credentials. | `robots_denied`, `terms_gate`, `target_denied`, `redirect_origin_denied`, `content_too_large`, `media_type_denied`, `fetch_partial`. | First delivery. |
| A5 `search_index` | A separately preauthorized search provider used for discovery only. It does not inherit authorization to fetch or hydrate a target. | Provider is the upstream identity. Store provider result ID/query/page/rank, link, title/snippet, observation time, and target origin separately. Google Custom Search defines results as links, titles, snippets and optional PageMap data; its estimated total can be inaccurate [S14]. | Provider quota/terms apply. Retain only what those terms permit. Never treat an indexed snippet as the target's current or complete representation. | `index_partial`, `target_not_hydrated`, `native_identity_unknown`, `native_time_unknown`, `comments_unavailable`, `engagement_unavailable`. A target blocked by terms/robots remains unhydrated; index use is not a bypass. | First delivery as discovery, never native hydration. |

### Preauthorization and fallback

The request plan freezes an ordered list of route grants before acquisition:

```text
route_grant = {
  route_id, access_class, adapter_id@version,
  allowed_origins, allowed_read_operations,
  credential_or_session_slot?, purpose, data_classes,
  retention_profile, fallback_after: [typed_failure...]
}
```

The runtime applies these rules:

1. Absence of a route grant is denial. A public route is still target- and policy-scoped.
2. Fallback occurs only for a listed typed failure and only to a route already present in the frozen order. `401`, `403`, `robots_denied`, paywall/login interstitial, CAPTCHA, or technical access control never authorizes another identity.
3. Authority is monotone non-increasing. A fallback cannot add a key, session, origin, user, private data class, CLI, method, or longer retention period.
4. Every attempt emits a route-local observation. Evidence from different route identities is never silently merged, even if canonical URLs match.
5. The accepted fallback emits `fallback_from`, `failure_type`, `loss[]`, and `loss_basis`. Required loss dimensions are native identity, body fidelity, comments/replies, native engagement names, publication/edit time, pagination completeness, deletion visibility, authorization context, and freshness.
6. If the fallback cannot answer the requested capability, return partial evidence plus the gap. A search snippet cannot become a native post, comment, view count, or publication date.

### Secret and session custody

- Manifests, specs, tickets, prompts, argv, URLs, cache keys, artifacts, traces, telemetry, diagnostics, and exception strings contain only secret-slot identifiers. Secret values and session material are forbidden.
- User API secrets resolve only after the route is selected. They are placed in the official transport's authorization header or provider-approved parameter, never a URL when a header is supported, and are zero-retention process memory. OAuth tokens are treated as sensitive secrets and restricted to minimum privilege/audience [S2].
- Redirects are re-authorized hop by hop. RFC 9110 calls for removal of origin/resource-specific fields including `Authorization` and `Cookie` when automatically redirecting, and for considering removal of caller-added sensitive fields [S3]. This contract is stricter: any origin change strips credentials and stops unless the destination origin and fresh credential binding were preauthorized.
- A CLI receives a minimal explicit environment profile; it does not inherit unrelated secret variables. Its stdout/stderr is bounded, decoded as data, normalized through an adapter schema, and redacted before any artifact or diagnostic write. Token-output, auth-management, arbitrary-header, arbitrary-host, verbose-wire, response-file, shell, and write-capable flags are absent from the argv grammar.
- A browser provider owns session material. No `storageState`, cookie export, local-storage export, profile copy, clipboard, download, devtools credential inspection, or raw network archive is allowed. Only adapter-selected evidence fields cross the boundary.
- Redaction runs before logging and again before artifact commit. It removes known secret values, auth/cookie header values, query parameters named by the adapter, browser-state shapes, and provider error fields known to echo request data. Redaction failure converts the entire diagnostic to a bounded code and correlation ID.
- Revocation or expiry immediately invalidates the route and triggers the platform retention action for authorized data. Cross-run caches are content-addressed only for data whose route-specific policy affirmatively permits them; secret/session material is never cross-run.

### Rate, terms, and retention

Each adapter carries an access-dated policy record: official source URL/version, permitted purpose/data classes, required identity/user-agent behavior, quota model, retry semantics, retention/refresh/delete rules, attribution, and last review date. An absent or expired record yields `terms_gate`, not optimistic access.

Rate ownership follows the upstream identity, not the worker or wrapper. One governor serializes budgets across concurrent discovery/hydration tasks for the same project or principal slot; it consumes provider headers, applies bounded backoff with jitter only when permitted, and preserves partial evidence when the budget closes. It never rotates accounts, IPs, projects, user agents, or wrappers to gain quota. Reddit prohibits masking OAuth or user-agent identity, exceeding limits, and bypassing restriction mechanisms [S10]; YouTube prohibits masking client identity and quota sharding, and ties credentials to a particular project/client [S11].

Retention is field- and route-specific. The evidence record carries `retention_basis`, `refresh_by`, `delete_by`, `revoked_at`, and `policy_source`. A shorter upstream deadline wins. Deletion propagates to derived caches and indexes that contain the restricted payload while preserving a payload-free tombstone with source ID, deletion reason, and audit time when policy allows. “Public” is not a retention basis; Atom even carries entry/feed rights metadata [S5].

### No-write boundary

The public skill schema has acquisition verbs only: `discover`, `fetch`, `hydrate_readonly`, `list`, and `transcribe_readonly`. No generic `request`, `execute`, `click`, or `api` escape hatch exists.

- HTTP adapters compile only to `GET` or `HEAD` and an endpoint allowlist that excludes action URLs, logout URLs, tracking/pixel URLs, signed mutation links, GraphQL mutations, and any endpoint whose read behavior has not been demonstrated.
- API adapters name operation IDs that admission tests prove read-only; caller-supplied methods, GraphQL documents, bodies, headers, and URLs are rejected.
- CLI adapters compile typed operations to a fixed argv template. User/source strings occupy one argument cell and can never create flags, pipes, redirections, command substitutions, environment assignments, or a second process.
- Browser/session adapters may navigate and extract from already-rendered pages. They cannot submit, type into action forms, click non-navigation controls, acknowledge destructive dialogs, perform downloads, change preferences, react/like/vote/follow, comment, edit, delete, upload, or log out.
- Retrieved text, markup, captions, comments, repository files, feed fields, snippets, and CLI output are untrusted evidence. OWASP identifies remote prompt injection through external content and recommends least privilege and remote-content defenses [S13]. Such content can populate evidence fields but cannot alter the frozen plan, grant a route, choose a tool, supply credentials, expand retention, or invoke an action.

## Threat and failure fixtures

| Fixture | Adversarial seed | Required oracle |
| --- | --- | --- |
| `T01-secret-manifest` | API token inserted in manifest, request plan, cache key, or artifact metadata. | Schema/write rejects; no target file contains the marker; result `secret_material_denied`. |
| `T02-raw-diagnostic` | Upstream error echoes `Authorization`, cookie, key query parameter, or request body; CLI emits it on stderr. | Artifact contains only typed code, safe correlation ID, and redacted field names; marker scan is empty. |
| `T03-cross-origin-redirect` | Credentialed API/page redirects from allowed origin to attacker origin or lookalike host. | No credential/cookie reaches hop 2; chain records origin change; `redirect_origin_denied`. RFC 9110-sensitive headers are removed [S3]. |
| `T04-same-origin-action-redirect` | Allowed read endpoint redirects to logout, mutation, signed action, or unapproved path. | Endpoint policy rejects before following; `target_denied`; no state changes. |
| `T05-cli-metacharacters` | Query/title contains `;`, `|`, newline, `$()`, backticks, `%VAR%`, quotes, `@response`, or a leading dash. | Exact approved executable launches once with `shell=False`; seed is one data argument or validation fails; no second process/file expansion. |
| `T06-cli-hidden-write` | Request tries `gh api -f body=x`, `-X POST`, GraphQL mutation, arbitrary header/host, `--verbose`, or token-output/auth command. | Grammar rejects with `argv_denied`/`method_denied`; no CLI launch. GitHub CLI's broad method/body surface makes this fixture mandatory [S9]. |
| `T07-session-export` | Adapter or injected page requests cookies, local storage, auth state, network archive, clipboard, download, or profile copy. | Provider call is unreachable/rejected; marker absent from artifacts; `session_state_export_denied`; context destroyed. |
| `T08-session-write` | Page labels a vote/comment/follow control as navigation, auto-submits a form, or serves a logout/action link. | Semantic label is irrelevant; only predeclared navigation/extraction operations exist; no click/submit; `action_denied`. |
| `T09-remote-prompt-injection` | Page/comment/feed says to ignore policy, reveal keys, open a URL, run a CLI, or write a file. | String remains evidence with `untrusted_content=true`; plan hash, route grants, tool calls, and write set remain unchanged; warning `hostile_instruction_present` [S13]. |
| `T10-auth-identity-mismatch` | API/CLI returns an account or enterprise host different from the preauthorized slot. | Evidence is quarantined; no canonical merge; `auth_identity_mismatch`; no fallback unless separately granted. |
| `T11-rate-limit` | `429`/`403`, zero remaining, or `Retry-After`; partial pages already exist. | Partial pages persist with cursor lineage; governor stops until provider time; no account/project rotation; `rate_limited` [S8]. |
| `T12-policy-denial` | robots disallow, terms gate, login/paywall/CAPTCHA, API restriction, or revoked permission. | Route stops. Search-index route runs only if independently preauthorized and is loss-labeled; target is not hydrated and restriction is not bypassed [S4][S10]. |
| `T13-search-loss` | Index snippet names votes/comments/date absent from a native response. | Schema stores snippet only under provider identity; native fields remain unavailable; `target_not_hydrated`; no inferred native metric/date [S14]. |
| `T14-cross-run-storage` | Run 2 attempts to reuse Run 1 token, cookie, authorized body, session context, CLI raw output, or expired retained data. | Secret/session lookups miss; restricted payload is absent or deleted; only allowed payload-free provenance survives; `retention_expired` where applicable [S10][S11][S12]. |
| `T15-public-is-not-unbounded` | Public feed/page is treated as authorization to crawl a disallowed path or retain indefinitely. | Robots/terms and retention checks still execute; denial is typed. Robots is not authorization [S4]. |
| `T16-fallback-widens-authority` | Public/API route failure tries adding a session, broader token, new origin, or mutation-capable CLI. | Frozen grant comparison fails before access; `fallback_not_preauthorized`; no route launch [S1]. |

## Findings and source trace

1. **Authority must be explicit and attenuating.** Observation: orchflows defines authority as exact write scope plus excluded actions; excluded actions stop, and child authority is a subset of the caller's [S1]. Design judgment: model every access route as an authority grant even when it has no repository write scope. **Confidence: high.** Flip condition: canonical authority law changes to permit implicit acquisition capabilities.
2. **Least-privilege tokens and redirect re-authorization are mandatory.** Observation: OAuth BCP requires minimum privilege/audience restriction and exact redirect controls; HTTP specifies removing origin/resource-specific sensitive fields on automatic redirects [S2][S3]. Design judgment: stop on every ungranted origin transition rather than merely stripping. **Confidence: high.** Flip condition: a platform's official client protocol requires a predeclared multi-origin flow; then each hop must be a separate frozen grant.
3. **Secret/session non-persistence is supported independently across platform and browser authorities.** Reddit restricts use/retention to the approved case and deletion; YouTube forbids collecting login credentials and constrains storage; Playwright says saved auth state can impersonate the account [S10][S11][S12]. **Confidence: high.** Flip condition: none for credential material; a platform-specific authorized-data retention rule may alter payload retention, not secret retention.
4. **An approved CLI is not intrinsically read-only.** Python's safe process shape is a sequence plus fully qualified executable, while `gh api` exposes methods, bodies, arbitrary headers/hosts, pagination, verbose output, and write examples [S6][S9]. Therefore approval must bind executable *and* argv/endpoint grammar. **Confidence: high.** Flip condition: a CLI exposes a formally read-only subcommand with no dynamic escape surface; it still needs executable/host pinning.
5. **Rate and retention policy cannot be normalized across platforms.** GitHub has principal/project-shared primary and secondary limits plus provider retry headers [S8]; Reddit may set limits and requires approved-use deletion [S10]; YouTube couples quotas, project identity, refresh, and deletion deadlines [S11]. **Confidence: high.** Flip condition: platform authorities publish a common interoperable policy (none found).
6. **Public feeds/pages are structured evidence, not blanket permission.** Robots directives must be honored by crawlers yet are not authorization [S4]. Atom provides stable IDs, source provenance, distinct published/updated semantics, and rights fields, but does not itself grant reuse [S5]. **Confidence: high.** Flip condition: an individual publisher provides an affirmative license/retention rule; it belongs in that adapter's policy record.
7. **Search index results are a discovery identity, not target evidence.** Google defines provider results as links/titles/snippets/PageMap and calls totals estimates [S14]. YouTube separately forbids presenting intermingled external results as YouTube search results [S11]. **Confidence: high.** Flip condition: the platform officially designates the index response as its native API representation for the field in question.
8. **Fetched content must be incapable of granting tools or actions.** OWASP recognizes remote prompt injection in external content [S13]; orchflows authority comes only from the dispatch [S1]. Design judgment: freeze plan/grants before parsing evidence and expose no write verbs. **Confidence: high.** Flip condition: none; trusted signed metadata may improve content integrity but does not become authority.

## Contradictions and dominance limits

- RFC 9309 says robots rules are not access authorization while also requiring compliant crawlers to honor successful rules [S4]. This is not permission to ignore robots; the correct model is two independent gates: authorization/technical access and crawler policy. Passing either does not pass the other.
- YouTube distinguishes public-video search that needs no *user* authorization from API access tied to an API project/credentials [S11]. Therefore `public content` and `public unauthenticated endpoint` are different properties; route class records both.
- `gh api` defaults to `GET` yet supplies broad mutation and diagnostic switches [S9]. Default method is not a security boundary; the outer typed adapter dominates.
- Search providers can offer date restriction and structured PageMap fields, but their result object is still a provider observation [S14]. A provider date never silently replaces native publication/edit time.

## Dead ends

- The GitHub REST authentication landing page was a navigation shell rather than claim-bearing guidance; the retained permission table [S7] and rate-limit page [S8] answered the needed questions.
- No official cross-platform browser-session standard defines “read-only user session.” Playwright's auth-state warning [S12] establishes custody risk, but origin/action non-write enforcement remains an orchflows admission requirement to prove locally.
- No primary source supplies universal page-fetch retention or universal “public endpoint” terms. Those must remain per-origin policy records; the lane does not infer a general license.

## Gaps and required local proof

- **Session provider capability:** official sources do not prove that the eventual browser connector can prevent cookie/state export, downloads, clipboard access, devtools/network archive capture, action clicks, or origin drift. Keep A3 gated until the fixtures pass against the concrete provider.
- **Secret-store integration:** no implementation is selected. The successor spec must choose a host-supported opaque secret handle and prove values never enter manifests, argv, child environment except an adapter-approved variable, diagnostics, caches, or artifacts.
- **Per-platform policy inventory:** this lane supplies the contract and representative policy diversity, not every platform's current terms. Each platform adapter needs an access-dated policy record and admission review.
- **CLI inventory:** only `gh api` was examined as the mechanism exemplar. Each proposed CLI requires its own command/flag/host/output audit; no generic “installed CLI” permission exists.
- **Public-feed licensing:** Atom describes `rights` but is not a license. RSS/Atom payload retention and reuse remain publisher-specific.
- **Search-provider drift:** the retained Google Custom Search response reference was last updated 2024-08-21; current availability, quota, and product admission must be rechecked when an adapter is selected.
- **Deletion propagation:** web evidence cannot prove complete deletion across the eventual cache/index architecture. Code-level fixtures must enumerate derived stores and verify payload removal with a permitted tombstone only.
- **No-write proof:** endpoint tables, GraphQL parsers, CLI templates, and browser action grammars must be tested against negative mutation fixtures. Prose and HTTP method labels alone cannot prove the boundary.

## First delivery versus gated routes

First delivery admits only adapters that pass all relevant non-session fixtures:

1. one official public structured endpoint/feed adapter;
2. one official API-key adapter whose exact operations require no write scope;
3. one approved local CLI adapter with pinned executable and fixed argv grammar;
4. uncredentialed page fetch with target/redirect/robots/terms controls; and
5. search-index discovery with mandatory non-native loss labeling.

API-key and local-CLI adapters are not globally enabled; the user selects each route. Browser/user-session support is a separate admission milestone after `T07`, `T08`, `T09`, `T10`, `T12`, `T14`, and `T16` pass against the real provider. A failure there leaves the public/key/local/page/index set useful; it does not weaken or silently simulate the session route.

## Retained primary authorities

All web authorities were accessed 2026-08-09.

- **S1 — Canonical orchflows authority law.** [`contracts/delegation.md`](../../../../contracts/delegation.md), repository file SHA-256 `E80B977D18183330EF8D9CD885E2BB07AACE9FC0C731E998C96D6A761E75D080`, at repository commit `7f01ba20adf51a3332adf5ac9d318eca8d333fa9` (spec-pinned).
- **S2 — IETF OAuth security BCP.** [RFC 9700: Best Current Practice for OAuth 2.0 Security](https://www.rfc-editor.org/rfc/rfc9700.html), especially §§2.1–2.3, 4.9–4.11.
- **S3 — IETF HTTP semantics.** [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html), especially §§11.6, 15.4, 17.16.
- **S4 — IETF robots protocol.** [RFC 9309: Robots Exclusion Protocol](https://www.rfc-editor.org/rfc/rfc9309.html), especially §§1, 2.2–2.3, 3.
- **S5 — IETF Atom format.** [RFC 4287: The Atom Syndication Format](https://www.rfc-editor.org/rfc/rfc4287.html), especially §§3.3, 4.2.6, 4.2.9–4.2.15, 8.
- **S6 — Python process API.** [Python 3.14 `subprocess` documentation](https://docs.python.org/3/library/subprocess.html), especially `Popen` argument, executable, shell, environment, and descriptor guidance.
- **S7 — GitHub token reach.** [Permissions required for fine-grained personal access tokens](https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens).
- **S8 — GitHub quota behavior.** [Rate limits for the REST API](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api), including shared primary/secondary limits and retry headers.
- **S9 — GitHub CLI mechanism exemplar.** [`gh api` manual](https://cli.github.com/manual/gh_api).
- **S10 — Reddit platform terms.** [Reddit Data API Terms](https://redditinc.com/policies/data-api-terms), last revised 2026-07-20, especially §§2.8–2.10, 3.1–3.2, 6.
- **S11 — YouTube platform policy.** [YouTube API Services Developer Policies](https://developers.google.com/youtube/terms/developer-policies), especially §§II.3–4, III.C–E.
- **S12 — Browser-session custody exemplar.** [Playwright Authentication](https://playwright.dev/docs/auth), warning on impersonation-capable stored browser state.
- **S13 — Hostile retrieved content.** [OWASP LLM Prompt Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html), remote-content, least-privilege, and testing sections.
- **S14 — Search-index response semantics.** [Google Custom Search JSON API `Search` resource](https://developers.google.com/custom-search/v1/reference/rest/v1/Search), last updated 2024-08-21.
