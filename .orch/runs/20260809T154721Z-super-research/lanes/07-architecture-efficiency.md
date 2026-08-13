# Lane 07: architecture and acquisition efficiency

- run: 20260809T154721Z-super-research
- ticket: 07-architecture-efficiency
- as_of: 2026-08-10
- status: complete
- independence: blind; no sibling lane was read
- verification: UNVERIFIED because the dispatch named no independent lane oracle; the four ticket completion tests are covered below and remain subject to terminal synthesis and gate

This packet is a local architecture judgment, not an implementation. O means an observation in a fixed source, C a canonical constraint, J a design judgment, and G an unresolved gap.

## Fixed source trace

| ID | Fixed local source | Use |
| --- | --- | --- |
| R0 | Current frozen research spec, SHA-256 4952B1695DC3296203B74720C65E08616DFEDCB56BDEA09D8CD51090BC3CDB89 | Clarified required scenarios, access ladder, timeliness, live-adapter floor, failures, and complete-delta requirement |
| T0 | Lane ticket, SHA-256 C02229E48DB952EBB4E0EECA91C44BE4CEA91FD630704F0B30582BB4A1D693E3 | Four completion tests and local-only bound |
| P0 | Accepted Pareto synthesis, SHA-256 BA71FD755898546FC1027BC07C5A9B8264517263721AF37F3819F4CE32A65EC2 | Static calls, phased acquisition, artifact identity, failure visibility, ownership, exact grouping, and removal falsifiers |
| F0 | Superseded fake-only code spec, SHA-256 7F9CE10EEF0251488EE75920AA6ABE431BDFB52AF605FD509F04AF8EB6C25A91 | Complete module, seam, criterion, test, and scope baseline |
| A0 | ARCHITECTURE.md at repository commit 7f01ba20adf51a3332adf5ac9d318eca8d333fa9 | Tier ownership, dependency direction, package-local scripts, and runtime-state boundary |
| V0 | docs/vocabulary.md at the same commit | Exact meanings of skill, kernel, scope, ticket, lane, evidence, oracle, and provenance |
| R1 | Installed research-pack craft and oracle policy, SHA-256 BAC545E57D344CB1ACD8A5900982B714F827B4291525680D72273F6A7CA51081 and F6F6D3728026C65F96309907EF857F2392D59C87EB38755784FABBCE6BBC9D7 | Atomic claims, observation/inference split, gaps, independence, and evidence oracle |
| C0 | packs/orch-code-pack/references/craft.md and oracles.md at the repository commit | Explicit searchable seams, locality, deterministic behavior tests, and judged code lens |
| S0 | skills/workflows/orch-build/SKILL.md and references/scopes.md at the repository commit | Project custom-item landing, resolver, host mirror, routing line, and library-lens admission |

## Result

The smallest architecture that satisfies R0 is still one project-scoped acquisition utility called by ordinary orchflows research, but it can no longer be fake-only or page-only. Its package-local acquisition core has:

1. one versioned manifest and one acquisition-artifact family;
2. two adapter operations, discover and hydrate, plus one pure project operation that never performs I/O;
3. a literal adapter roster and literal call branch for every adapter;
4. a common cursor-page contract, bounded scheduler, deterministic normalizer, exact grouping, views, and context projection;
5. six first-delivery live adapters plus the retained fake adapter;
6. distinct public-endpoint, API-credential, local-tool, user-session, page-fetch, and search-index access classes; and
7. ordinary research ownership of query/source-role freeze, candidate and payload selection, findings, independence, confidence, contradiction judgment, and synthesis.

The requested “kernel” is therefore a package-local acquisition core. It is not an orchflows kernel and changes no canonical kernel, T0 contract, pack, composition, or top-level script. This preserves A0/V0/S0 while reversing only the fake-only delivery decision that R0 explicitly invalidates. P0 C02/C04/C06/C07/C08/C14 support the retained shape; P0 O05/C13 already says comments and transcripts re-enter when a required scenario exists, and R0 supplies that scenario.

## Completion test 1: exact ownership and call graph

| Owner | Owns | Never owns |
| --- | --- | --- |
| Ordinary orchflows research ticket/lane | Question and interval freeze; source roles and slices; allowed access classes and ordered route chain; discovery candidate selection; required hydration payloads; record selection for context; findings, claim confidence, disagreements, gaps, and synthesis | Network/CLI details, cursor mechanics, hidden provider choice, or secret custody |
| Package acquisition core | Schema validation; pure authorization; stable eligible-route choice; preauthorized fallback conditions; global/per-source budgets; bounded concurrency; cursor loop; date stop; normalization; exact grouping; deterministic views; context projection; canonical artifact export | Query planning, automatic candidate selection, platform inference, provider-quality scoring, findings, or synthesis |
| One explicit adapter module | Literal endpoint or argv construction; one bounded upstream call; native schema parse; platform identity, native view, time, metric, cursor, and loss mapping | Calling another adapter, retrying, paginating invisibly, persisting, ranking across platforms, or interpreting evidence |
| Read transport | HTTPS GET/HEAD with redirect/target/byte/time bounds; or a literal approved argv with shell disabled; redaction and requested/final target trace | POST/write methods, arbitrary URLs for API adapters, arbitrary commands/subcommands, cookies/session values in artifacts, or fallback |
| Host/user configuration | Secret values, approved executable resolution, and opaque authorized session handle outside manifests and artifacts | Granting an adapter authority the caller did not name |

Static call graph:

~~~text
ordinary research lane
  -> AcquisitionManifest(discover)
     -> cli -> schema.validate -> router.authorize_and_route
     -> runner.schedule
        -> adapters.dispatch_discover          # literal if/elif branches
           -> adapter.build_request
           -> transport.read
           -> adapter.parse_page
        -> runner cursor/date/cap loop
        -> normalize -> project.views -> canonical AcquisitionArtifact
  <- bounded discovery candidates
  -> lane selects candidate IDs and required payloads
  -> AcquisitionManifest(hydrate, prior artifact, selected IDs)
     -> same validation/authorization/scheduler
        -> adapters.dispatch_hydrate           # literal if/elif branches
        -> serial cursor pages per item; bounded items concurrent
        -> normalize -> group -> views -> artifact
  <- acquired evidence records
  -> lane selects record IDs
  -> ProjectionManifest -> project.context     # pure; zero adapter calls
  -> lane creates findings; orchflows synthesis judges claims
~~~

Each adapter call returns exactly one NativePage with records, cursor_out, native order declaration, timing, warnings, native outcome, and loss. Runner, not the adapter, decides whether another page is authorized. A direct known locator enters as a caller-frozen seed ID; it does not give the core selection authority. An upstream response that already contains every requested payload may mark the record complete and avoid hydration, but still emits discovery and hydration-state lineage.

Concurrency ownership is deliberately narrow:

- discovery source slices and independent selected hydration items may run concurrently;
- runner owns one global max_in_flight and one hard per-adapter limit;
- pages for one cursor chain and pages of one comment tree are serial, so date and terminal-bound stops remain valid;
- one page has one attempt: no retry, sleep, or hidden engine fan-out;
- output order is manifest slice, selected candidate, page, then native position, independent of completion order;
- rate, deadline, or cap termination preserves completed records as partial evidence and authorizes no extra call.

## Completion test 2: common evidence and timeliness model

AcquisitionManifest v2 is the only request family. It contains manifest/phase/slice/request IDs; discover query or direct seed; prior artifact and selected candidate IDs for hydrate; required source role, platform family, content kinds and payloads; requested time interval and basis; requested native view; ordered preauthorized routes; and hard call/page/item/byte/time/comment/reply/transcript/context caps. It contains no token, cookie, credential reference, profile path, arbitrary module, command, or endpoint.

AcquisitionArtifact v2 is the only public acquisition result family. Every attempt and record retains:

| Family | Required common fields |
| --- | --- |
| Identity | artifact, manifest, phase, slice, request, attempt, candidate, record, adapter and adapter-schema version |
| Platform relation | platform family, content kind, native item ID when supplied, thread/root ID, parent ID, canonical locator, author and community identities; explicit loss when a route cannot supply them |
| Content | title/text/media locator, media type/language, exact content hash, truncation and payload-completeness flags; transcript segments add media ID and start/end offsets |
| Time | requested and applied interval, requested basis published or updated, published_at, edited_at, observed_at, engagement_observed_at, time confidence authoritative/reported/derived/unknown, time source and precision |
| Engagement | a list of namespaced native metric snapshots: platform namespace, native metric name, numeric/string value, and observation time; values are never normalized across platforms |
| Order and page lineage | requested view, native view, native rank/position, page index, cursor_in/out, and whether the active native order has a proven monotonic time guarantee |
| Access/provenance | access class, route provider identity, source upstream identity when known, requested/final target, discovery query/hit lineage, and policy/configuration version without secret values |
| Outcome | ok, empty, partial, failed, or refused; typed auth, rate, policy, target, schema, timeout, unavailable, unsupported, or budget reason; warnings and explicit field/content/coverage loss |
| Audit | requested and consumed calls/pages/items/bytes/duration per slice; opaque provider usage may survive but cannot authorize another call |
| Native extension | bounded, namespaced, adapter-schema-versioned native metadata; it may not replace any common field |

Content kinds cover web_hit, web_page, post, thread, comment, reply, media, transcript_segment, feed_item, repository, commit, issue, pull_request, discussion, release, and generated_text. Generated provider prose remains acquired content and never a finding.

Timeliness is executable:

1. The manifest freezes closed-open start/end and time basis. Each attempt records what the route applied upstream and what the core filtered locally.
2. A hard-interval record with stale or unknown basis time cannot be ok. It remains excluded or partial with explicit loss. Edited time never substitutes for publication time unless updated is the caller-frozen basis.
3. Early date stop is legal only when the descriptor and active native view guarantee non-increasing authoritative times and every page item needed for the decision has a known time. The first wholly older page terminates before the next call.
4. Top, most-commented, and most-replied pages are not presumed time-monotone. They use server interval enforcement where supported, otherwise bounded local filtering and a recall-loss label.
5. Independent page, item, byte, deadline, comment-count, reply-depth, and transcript-segment caps terminate before another call and record the exact terminal reason.
6. Every source slice has its own cap; a global cap cannot let one platform consume another required role. Unused source capacity is not silently reallocated.
7. Raw order is stable. A cross-source chronological projection may order records with usable requested-basis times, with unknown dates in a separate bucket. native_top, most_commented, and most_replied are emitted only within one platform/metric namespace; they order attention, never authority or confidence.
8. Engagement observations are append-only snapshots. A later vote/comment/view count does not overwrite the earlier observation.

Wrong-merge policy is conservative:

- records sharing platform, native item ID, and content kind form an identity group but retain each observation and engagement snapshot;
- otherwise an exact-content group requires normalized final locator, content kind, and exact content hash;
- a comment/reply never merges with its thread or parent;
- a changed body at the same URL stays distinct;
- cross-platform matches are duplicate-group links, not identity merges;
- provider/source plurality never establishes upstream independence;
- raw acquisition caps count all received items, while exact duplicates do not displace unique groups under the context cap.

The pure context projection receives caller-selected record IDs. It emits one payload per exact group, all provenance, the selected comment/reply ancestor chain, and only caller-named transcript neighbor windows. It neither retrieves nor selects evidence. The immutable bounded artifact remains complete even when projected context is small.

## Completion test 3: efficiency design and falsifiers

No retrieval-quality superiority is claimed. The mechanical claims below compare identical frozen selections and payload requirements.

| Decision | Calls/content/model work avoided | Deciding fixture; result that falsifies it |
| --- | --- | --- |
| Discover, then lane selection, then hydrate | Avoids hydrate calls and response bytes for unselected candidates | Same candidates and required payloads: hydrate-all must not use equal/fewer calls and bytes with no worse required-record yield; if it does, the split is not more efficient |
| Payload-specific hydration | Avoids comment, reply, page-body, engagement, or transcript calls not named for a selected item | A fixture where conditional payloads lose a required record or make as many calls/bytes as full hydration falsifies the saving; required payloads may never be dropped for economy |
| Complete-at-discovery short circuit | Avoids a second call only when every requested field is already present with lineage | A fused response missing native identity, dates, comments, metrics, or loss but marked complete falsifies the rule |
| Monotonic date-boundary stop | Avoids every page after the first wholly older page | An in-window item behind the asserted boundary, an unknown-time item needed for the decision, or an order violation falsifies the descriptor and disables the stop |
| Per-source and per-payload caps | Avoids long-tail pages, deep replies, and transcript bytes after the frozen cap | A required-scenario fixture whose only decisive evidence lies beyond the cap falsifies that cap; the caller must widen it explicitly |
| Bounded cross-source/item concurrency | Avoids wall-clock wait only; it avoids no call, byte, or model work | Fake-clock/barrier replay showing no elapsed improvement, rate amplification, cap overshoot, or unstable output falsifies the concurrency setting |
| Exact grouping before projection | Avoids duplicate context bytes; it does not authorize extra retrieval | Any false merge, provenance loss, changed-content collapse, or unique-record displacement falsifies the key |
| Selected context plus ancestor chain | Avoids full-thread/full-transcript model input bytes | A claim fixture that cannot be judged from the selected records plus required ancestors/windows, or equal-sized output, falsifies the projection |
| Cursor loop in the core | Avoids hidden adapter over-fetch and exposes the first terminal bound | A call ledger containing an adapter-owned second request or a call after a stop falsifies the seam |
| No cache, async jobs, model extraction, or provider writer | Avoids cache lifecycle, poll calls, prompt/model work, and duplicate research ownership | A required workload that cannot finish synchronously, or a frozen repeat workload proving safe cache/model benefit without custody or evidence regression, reopens only that feature |

Benchmark/admission baseline:

- Five frozen workloads: recent web/news page; recent Reddit-like thread with bounded comments/replies and changing engagement; video with transcript segments; code/community activity; RSS/Atom entries with selected page hydration.
- Compare naive hydrate-all/sequential/no-date-stop/full-context behavior against the selected core with identical source slices, required payloads, caps, and recorded upstream pages.
- Record required-scenario pass, typed-loss correctness, calls, pages, input/output bytes, elapsed fake-clock time, projected context bytes, false merges, provenance completeness, secret/write violations, and deterministic bytes.
- Provider quality, price, availability, and cross-platform popularity are outside this comparison until a common authorized time-pinned workload exists.

## Completion test 4: first live adapters and complete fake-only delta

### First live adapter set

The smallest release floor is six literal modules. “Initial” means implemented and admitted; it does not mean automatically authorized. Each non-public route is fail-closed until its access gate is satisfied.

| Literal adapter ID and file | Access class | Required capability | Initial limits / explicit loss |
| --- | --- | --- | --- |
| brave_web_search / adapters/brave_web_search.py | api_credential plus search_index mechanism | Web discovery with hit rank, locator, requested/applied interval and reported publication time | Discovery only; cannot supply native platform comments/engagement and cannot turn index dates into authoritative platform dates |
| public_page / adapters/public_page.py | page_fetch | Selected HTTPS page body, links, media type, requested/final target and observed time | Static public content only; JS-only, blocked, PDF/media-unsupported, robots/policy-uncertain, and off-policy redirect targets fail with typed loss |
| reddit_api / adapters/reddit_api.py | api_credential | Reddit-like posts, threads, bounded comments/replies, native order, published/edited times and native engagement snapshots | Read-only official route; no key/session in artifacts; unavailable fields or access restrictions remain partial/refused |
| youtube_ytdlp / adapters/youtube_ytdlp.py | local_tool | Known-video metadata and bounded captions/transcript segments with publication and observation time | Literal approved executable and argv only, shell disabled; no promise of captions where the platform supplies none; admission requires current compliant route evidence |
| github_gh / adapters/github_gh.py | local_tool, with separately authorized external CLI session when configured | Repositories, issues, discussions, releases, comments/reactions and dates | Literal read-only gh subcommands/endpoints; private content and session handle are gated; mutation subcommands are unreachable |
| rss_atom / adapters/rss_atom.py | public_endpoint | RSS/Atom feed discovery, entry identity/content/date/author/link and cursor/page lineage | Feed data only; missing dates remain unknown; full-page/comments/engagement require another selected adapter |

The retained adapters/fake.py proves contracts but never satisfies a live capability row. P0 directly supports Brave-like search separation and hardcoded CLI/public routes as candidates; the exact Reddit, video, code, and feed protocol/terms claims must be supplied by their owning platform lanes at synthesis. If those lanes reject one named route, the six capability slots stay fixed and the adapter ID changes before the successor spec freezes.

Later gated modules are not stubs or dynamic plugins. They enter the literal roster only after separate admission:

- user_session adapters for platforms whose compliant read path requires an already-authorized session;
- additional social/regional/specialized APIs or approved CLIs;
- authenticated private code/community routes;
- dynamic-browser page hydration;
- alternate web search routes and search-index fallbacks;
- map/crawl or async-job adapters.

Every admitted adapter must pin its primary protocol/access evidence, access class, data and loss matrix, endpoint/argv builder, native schema fixture, rate/cursor/date behavior, dependency/version, read-only threat cases, sanitized golden responses, schema-drift seed, and one explicit authorized live smoke artifact. Search-index or page fallback cannot claim native comments, engagement, transcript, or authoritative platform date when absent.

### Exact affected surfaces

Retain and widen:

- .orchflows/skills/search-fusion/SKILL.md
- .orchflows/skills/search-fusion/references/protocol.md
- .orchflows/skills/search-fusion/scripts/search_fusion/__init__.py
- .orchflows/skills/search-fusion/scripts/search_fusion/schema.py
- .orchflows/skills/search-fusion/scripts/search_fusion/router.py
- .orchflows/skills/search-fusion/scripts/search_fusion/runner.py
- .orchflows/skills/search-fusion/scripts/search_fusion/normalize.py
- .orchflows/skills/search-fusion/scripts/search_fusion/cli.py
- .orchflows/skills/search-fusion/scripts/search_fusion/adapters/__init__.py
- .orchflows/skills/search-fusion/scripts/search_fusion/adapters/fake.py
- .claude/skills/search-fusion/SKILL.md
- AGENTS.md, one project-scope routing line outside managed blocks

Add:

- .orchflows/skills/search-fusion/scripts/search_fusion/transport.py
- .orchflows/skills/search-fusion/scripts/search_fusion/project.py
- the six adapter files named in the live-set table
- .orchflows/skills/search-fusion/tests/test_transport.py
- .orchflows/skills/search-fusion/tests/test_adapters.py
- .orchflows/skills/search-fusion/tests/test_context.py

Retain and widen the prior tests:

- test_dependency_boundary.py: literal imports/call branches, no dynamic import/registry, SDK, external skill, shell string, arbitrary executable/endpoint, write method, or forbidden dependency.
- test_router.py: six access classes, configuration-presence booleans only, zero-call refusals, payload/time/view capability, ordered preauthorized fallback, and every elimination reason.
- test_pipeline.py: discover-reference-select-hydrate, direct seed, cursor lineage, bounded concurrency, stable completion-independent order, page/date/call/byte/comment/reply/transcript stops, partial preservation, snapshots, chronological and within-platform views, and wrong merges.
- test_cli.py: canonical v2 JSON, live adapter selection through fixture transport, no secrets/session handles/findings, stable exit 0 completed/partial, 1 refused/no-route, 2 invalid/internal.
- tests/fixtures/**: sanitized per-adapter pages/stdout, goldens, fake clocks/barriers, malformed/drift/secret/write/stale/unknown/edited/changing-engagement/out-of-order-date/false-merge seeds, and live-smoke manifest templates without secret values.

test_transport.py proves HTTPS target/redirect/private-network/body/deadline bounds, GET/HEAD only, redaction, literal argv, shell disabled, bounded stdout/stderr, and no call after termination. test_adapters.py is the common descriptor/request/parser contract matrix for fake plus six live modules. test_context.py proves exact-group displacement, ancestor chains, transcript windows, provenance, deterministic bounds, and measured context-byte reduction.

references/protocol.md remains the one prose owner of manifest, artifact, access, adapter, failure, budget, ordering, and projection contracts. Do not recreate references/schemas.md or references/policy.md. No catalog.py, preflight.py, planner.py, fusion.py, enrichment.py, lifecycle.py, degradation.py, cache.py, dynamic registry, provider SDK, credential store, browser/session core, workflow/composition, T0 contract, canonical kernel, pack, top-level script, installer, or managed-block change is added.

Project scope is unchanged: the item lands under .orchflows/skills/search-fusion, its Claude mirror is only the host-legal include stub, AGENTS.md carries one routing line, and the user-scope installation resolves call edges. Runtime live-smoke/acquisition artifacts land only under the caller's .orch/runs/<run>/ and never become instructions.

### Criterion-by-criterion delta from F0

| F0 criterion or constraint | Successor disposition |
| --- | --- |
| A1 original/static dependency boundary | Keep; widen forbidden cases to arbitrary HTTP endpoints, commands, write methods, SDKs, and adapter-to-adapter calls |
| A2 public-only static route | Widen to six access classes, explicit payload/time/view capability, configuration presence, and caller-preauthorized fallback; pure zero-call authorization remains |
| A3 discover then selected fetch | Widen to discover then lane selection then payload-specific hydrate; prior artifact/candidate identity and direct seed validation remain |
| A4 AcquisitionArtifact v1 | Supersede with v2 fields above: hierarchy, transcript offsets, timestamp confidence/source, engagement snapshots, cursor/page/access/upstream lineage and bounded usage; findings remain forbidden |
| A5 exact grouping/native order | Keep and strengthen with platform native identity, observation snapshots, cross-platform non-merge, chronological projection, and platform-local attention views |
| A6 sequential exactly once | Replace with bounded concurrent independent slices/items and serial cursor chains; each page still has one attempt, output stays deterministic, and no retry/hidden fan-out remains |
| A7 runner-owned expand_site | Keep as optional public_page hydration reuse under same-origin/page/depth/byte/time bounds; it is not a provider operation |
| A8 fake-only CLI tracer | Widen to fixture-driven six-adapter tracer plus separately authorized live-smoke mode; canonical outputs and ownership/exit prohibitions remain |
| A9 repository checks | Keep with resolved Python 3.9+: project tests, tools/validate.py, repository unittest suite, install.py --dry-run, and git diff --check |
| A10 independent code lens | Keep; fresh lens must also judge access, adapter locality, failure visibility, and scope |
| Standard-library-only, exactly two fake adapters | Core remains Python standard library; retain fake coverage, add six live modules; gh and yt-dlp are optional approved external tools invoked only by their literal gated adapters, never imported |
| Public/read-only only; no credentials/local/session | Preserve read-only and no secret persistence; add fail-closed API-credential and local-tool routes now, user-session routes only by separate admission |
| Comments/transcripts/enrichment deferred | Reverse: comments, replies, engagement, and transcripts are first-class requested hydrate payloads, not enrichment; model/CSS extraction remains deferred |
| No fallback | Reverse only to caller-frozen ordered routes with typed trigger and explicit loss; no implicit retry, relaxation, identity switch, or authority escalation |
| No ranking/source round robin | Preserve no cross-platform score/round robin; add required deterministic native platform views and cross-source chronology |
| Public counters absent | Reverse to bounded per-slice usage audit because live cap/rate/efficiency behavior is now required; no normalized price or cross-provider cost |
| No cache/async/model writer/planner | Keep absent |
| No live adapter file/credential reference/local CLI | Reverse live-adapter and approved-local-tool absence; secret values and session handles remain absent from every schema/artifact |

### Admission and exact oracles

The first dependency ticket must freeze all seven test files, fixture/golden identities, wrong-result seeds, adapter capability matrix, authorized live-smoke manifests, exact commands, and repository baseline before production code. Deterministic CI never uses a credential or network.

Required deterministic commands remain:

1. resolved Python 3.9+ -m unittest discover -s .orchflows/skills/search-fusion/tests -v
2. resolved Python 3.9+ tools/validate.py
3. resolved Python 3.9+ -m unittest discover -s tests -v
4. resolved Python 3.9+ install.py --dry-run
5. git diff --check

Each live adapter additionally runs the CLI live-smoke subcommand from the package scripts directory with a caller-authored manifest and externally configured authority. Its artifact must show one actual read-only route, redacted access, current observed time, bounded records or a typed live failure, and zero writes. A fixture test cannot substitute for this viability check; a live smoke cannot substitute for deterministic wrong-result fixtures. The successor code spec retains plan_gate: true.

## Load-bearing findings, confidence, and reversal evidence

| Finding | Type | Support | Confidence and what flips it |
| --- | --- | --- | --- |
| Ordinary research must remain the only judgment owner | O+C+J | P0 C01/C14; A0/V0 | High; only canonical supersession flips |
| One project utility with static adapters is smaller and more auditable than a plugin/provider workflow | O+C+J | P0 C02/C06 and exact-call removal test; C0/S0 | High shape confidence; a smaller searchable graph passing the same access/failure tests flips |
| Comments, replies, engagement and transcripts must be core payloads now | O+J | R0 acceptance 1/3/5/6; P0 O05/C13 re-admission rule | High requirement confidence; only a changed required scenario flips |
| Discover-select-hydrate preserves judgment and avoids unselected work | O+C+J | P0 C04 and F0 A3; R0 acceptance 5 | High ownership, medium efficiency; hydrate-all falsifier above flips efficiency |
| Runner-owned cursor/date/cap/concurrency makes calls visible and deterministic | J supported by O+C | P0 C05/C06/C09; C0 explicit seam; R0 acceptance 4/5 | Medium-high; hidden-call or concurrency/date fixtures flip individual choices |
| One record model can cover all required content without universal platform scores | J supported by O+C | P0 C06/C08/C12; R0 acceptance 3/4 | Medium-high; adapter fixtures requiring incompatible identity semantics force a versioned subtype, not platform score |
| Six literal adapters are the minimum first live floor | J | R0 acceptance 6; P0 candidate mechanisms | Medium; owning platform lanes may replace an adapter ID or show two required slots can be safely combined |
| Cache, async lifecycle, model extraction, provider planners/writers remain outside first delivery | O+C+J | P0 C10-C14 and falsifiers; R0 non-goals/risks | Medium-high; only a required workload plus its named admission evidence reopens one feature |

## Contradictions, dead ends, and gaps

Contradiction/supersession register:

1. F0 deliberately requires exactly two fake adapters and forbids live adapters, comments, transcripts, credentials, local tools, concurrency, and fallback. R0 explicitly says that outcome misses the goal and requires live broad evidence. This is a frozen requirement supersession, not evidence averaged away.
2. P0 selects sequential one-attempt execution for the fake baseline. R0 now names concurrency and broader live coverage. This packet preserves one attempt per page and deterministic order while adding bounded concurrency only across independent work.
3. F0 requires a route to enforce a hard interval or refuse. Search-index/page fallbacks may not enforce or supply authoritative dates. This packet preserves the hard-evidence rule: such routes may emit loss-labeled leads/partials but cannot counterfeit ok timely native evidence.

Dead ends:

- No sibling lane, web page, credential, API, CLI, authenticated session, or live target was consulted or executed.
- One combined local-source read was truncated; it was discarded, re-read in bounded chunks, and logged under the friction law.
- No provider-selection conclusion was inferred from product count, rank, or the accepted synthesis's links.

Gaps:

| Gap | Consequence | Required closure |
| --- | --- | --- |
| Platform-specific endpoints, terms, quotas, schema versions and current access are outside this local lane | The six adapter IDs are an architectural floor, not proof each named route is deployable on 2026-08-10 | Owning platform lane primary trace plus synthesis admission decision |
| No live call or authorized deployment | Availability, extraction fidelity, actual latency/rate behavior and secret redaction are unverified | Per-adapter authorized live-smoke artifact and deployment review |
| Page compliance cannot be certified by a generic algorithm | public_page must fail closed where target policy/robots/terms or redirects are uncertain | Target-policy fixtures and current deployment policy |
| Native pagination/date guarantees differ | Early date stop is enabled only per adapter/view with proof | Adapter protocol citation plus out-of-order/unknown-time wrong seeds |
| Public transcript access and approved CLI status may drift | youtube_ytdlp may be replaced or remain gated | Current primary platform/tool/terms evidence and executable/version approval |
| Cross-platform quality and optimal caps are unbenchmarked | No provider-quality winner or universal cap is claimed | Common time-pinned authorized workloads and equal-budget ablations |
| Session custody threat model is not locally proven | User-session adapters remain outside the initial literal roster | Separate target/origin/scope/read-only/redaction/failure threat suite |
| Dynamic HTML, PDF and unsupported media normalization is unproven | public_page emits typed partial/unsupported loss | Exact-content corpus or separately admitted browser/media adapter |

## Completion self-audit

1. Exact acquisition-core/adapter/orchflows ownership and call graph: covered.
2. Common evidence model for web, posts, comments, transcripts, feeds and code, including time confidence and native engagement snapshots: covered.
3. Discovery-selection-hydration, concurrency, pagination/date stop, source caps, within-platform ordering, dedupe and context efficiency, with avoided work and falsifiers: covered.
4. Exact F0 surface/criterion/constraint delta and proposed six-adapter live floor: covered.

The lane is complete within its fixed local evidence bound. Terminal synthesis must resolve the named-adapter gaps against the six platform/access lanes before it treats any route as currently admitted.
