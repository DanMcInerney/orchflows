# Research spec: timely cross-platform super-research acquisition

- `run`: `20260809T154721Z-super-research`
- `objective`: An adversarial, current, primary-source-backed architecture exists for an original orchflows super-research skill that preserves the high-value platform coverage, public and user-authorized access paths, posts, threads, comments, engagement, transcripts, publication dates, and recency organization used across Agent Reach, Last30Days, and distinct adjacent tools, while improving efficiency, provenance, failure visibility, custody, and research ownership without copying or importing their skills or scripts.
- `non_goals`:
  - Implementing adapters or editing canonical/project code during this research run.
  - Copying third-party source, prompts, configurations, fixed weights, schemas, or dependency graphs.
  - Circumventing authentication, paywalls, anti-bot controls, rate limits, robots directives, platform terms, or technical access controls.
  - Treating engagement, provider rank, source count, or generated prose as truth or claim confidence.
  - Claiming complete platform coverage where no compliant, reproducible access path exists.
- `acceptance`:
  1. The synthesis inventories every platform, content type, and acquisition mechanism materially used by Agent Reach and Last30Days, plus only mechanism-distinct adjacent tools: posts, threads, comments/replies, votes/likes/reposts/views, transcripts/captions, news/feed items, code/repository activity, page content, publication/update/observation times, discovery, hydration, pagination, and sorting. Every omission is an explicit gap. Oracle: inventory-to-pinned-source coverage audit. `oracle_class`: `evidence`.
  2. For every retained platform family, an access ladder distinguishes official public structured endpoints/feeds, official API with user-supplied credentials, approved local CLI, user-authorized read-only session, compliant page fetch, and search-index fallback; it names data available, timeliness, custody, rate/retention/terms constraints, failure modes, and when a route cannot supply native engagement or comments. No route is described as bypassing a restriction. Oracle: current official repository/API/terms trace through 2026-08-09. `oracle_class`: `evidence`.
  3. A provider-neutral evidence model covers web results/pages, social posts, comment trees, media/transcripts, feeds/news, repository/issues/discussions/releases, and platform-native metadata while preserving platform item/thread/parent identities, canonical locator, author/community, content kind, published/edited/observed time, engagement snapshot with native metric names, cursor/page lineage, access path, upstream identity, warnings, partial failures, and explicit loss. Oracle: field-to-source and wrong-merge audit across all retained families. `oracle_class`: `judged`.
  4. The architecture makes timeliness executable: hard requested/applied intervals, publication-time confidence, observation and engagement-snapshot time, early pagination stop at the date boundary, newest/most-commented/most-replied/native-top deterministic views, per-source caps, source-role coverage, and stale/unknown-date handling. It states which orders are within-platform attention only and prohibits cross-platform engagement normalization as confidence. Oracle: scenario replay for recent community/news/product/code questions with stale, unknown, edited, and changing-engagement seeds. `oracle_class`: `judged`.
  5. The acquisition flow separates low-cost discovery from selected hydration of pages, threads, bounded comments/replies, and transcripts; it identifies concurrency ownership, per-platform budgets, conditional payloads, request-local dedupe, canonical grouping, pagination stops, and preservation of partial evidence. Every efficiency improvement names the calls/content/model work avoided and the fixture that would falsify it. Oracle: call/content/state comparison against the source-tool mechanisms and the prior fake-only spec. `oracle_class`: `evidence`.
  6. The proposed skill is modular but useful: it defines a hardcoded kernel, explicit adapter families, an initial live coverage set, separately gated authenticated/session adapters, and feature admission tests. The first usable delivery must perform live compliant research over more than fake adapters and must include at least one web-search route, one page-fetch route, Reddit-like posts/comments/engagement, one video/transcript route, one code/community route, and RSS/Atom feeds. Oracle: capability-to-scenario matrix and no-fake-only audit. `oracle_class`: `judged`.
  7. Authority, custody, and failure behavior are explicit: public, API-key, local-tool, and user-session routes are distinct; secrets never enter manifests/artifacts; write actions are unreachable; rate/auth/policy/target/schema/partial failures remain typed; fallback is preauthorized and loss-labeled; generated answers remain acquired artifacts. Oracle: threat/failure matrix over every access class and platform family. `oracle_class`: `judged`.
  8. A complete delta supersedes fake-only code spec SHA-256 `7F9CE10EEF0251488EE75920AA6ABE431BDFB52AF605FD509F04AF8EB6C25A91`, naming exactly what remains, widens, or is restored: live adapters, platform schemas, comments/transcripts, engagement/date views, access ladder, concurrency, adapter contract fixtures, dependencies, surfaces, and plan-gated delivery. No whole skill or external script is imported. Oracle: affected-surface and acceptance crosswalk. `oracle_class`: `evidence`.
  9. Observations, project/vendor claims, design judgments, and gaps remain distinct; current facts are pinned or access-dated, shared upstreams do not counterfeit independence, contradictions are registered, and web research states what only local contract/security/benchmark execution can prove. Oracle: final research-lens review and citation resolution audit. `oracle_class`: `judged`.
- `binding_constraints`:
  - Use exact orchflows vocabulary. Ordinary research delivery retains question freeze, lane cutting, independent evidence judgment, claim confidence, synthesis, gate, and verification.
  - Research mechanisms and access semantics, not products as indivisible wholes. Wrappers over the same upstream count once unless they change custody, failure, data shape, timeliness, or operating cost.
  - Primary sources only for load-bearing facts: pinned official repositories/source, official API/CLI documentation, platform terms/security/privacy material, and primary benchmark papers. Secondary sources may discover leads only.
  - Date mutable claims 2026-08-09 and pin repository claims to a commit when possible.
  - A compliant route may reduce API cost by using an official public feed/endpoint, approved local tool, user-supplied credential, or user-authorized read-only session. It may not evade a restriction or misrepresent incomplete search-index data as native platform data.
  - Engagement values remain namespaced snapshots. Cross-platform score normalization, provider agreement, and popularity never determine authority, independence, or confidence.
  - Preserve both prior accepted research synthesis `BA71FD75...A65EC2` and fake-only code spec `7F9CE10E...25A91` unchanged; the successor spec is written only after this synthesis is accepted.
- `evidence`:
  - User clarification dated 2026-08-09: the main value is timely access to posts, Reddit-like comments, votes/engagement, threads, transcripts, and date organization across everything the researched tools use; a fake-only core misses the goal.
  - Accepted Pareto synthesis `.orch/runs/20260809T132140Z-search-pareto/synthesis.md`, SHA-256 `BA71FD755898546FC1027BC07C5A9B8264517263721AF37F3819F4CE32A65EC2`.
  - Superseded fake-only code spec `.orch/runs/20260809T145250Z-search-pareto-native/spec.md`, SHA-256 `7F9CE10EEF0251488EE75920AA6ABE431BDFB52AF605FD509F04AF8EB6C25A91`.
  - Prior accepted lane packets for Agent Reach, Last30Days, public search/crawl, APIs, research orchestration, authenticated custody, and benchmarks under run `20260809T132140Z-search-pareto`.
  - Repository commit `7f01ba20adf51a3332adf5ac9d318eca8d333fa9` and canonical orchflows research/code/scoping contracts.
- `affected_surfaces`:
  - `.orch/runs/20260809T154721Z-super-research/spec.md`
  - `.orch/runs/20260809T154721Z-super-research/composition.md`
  - `.orch/runs/20260809T154721Z-super-research/worklog.md`
  - `.orch/runs/20260809T154721Z-super-research/lanes/01-anchors-platforms.md`
  - `.orch/runs/20260809T154721Z-super-research/lanes/02-social-community.md`
  - `.orch/runs/20260809T154721Z-super-research/lanes/03-media-code-feeds.md`
  - `.orch/runs/20260809T154721Z-super-research/lanes/04-regional-specialized.md`
  - `.orch/runs/20260809T154721Z-super-research/lanes/05-web-search-crawl.md`
  - `.orch/runs/20260809T154721Z-super-research/lanes/06-access-custody.md`
  - `.orch/runs/20260809T154721Z-super-research/lanes/07-architecture-efficiency.md`
  - `.orch/runs/20260809T154721Z-super-research/synthesis.md`
  - Shared ticket files under `C:\Users\danhm\tools\orchflows-public\.orch\tickets\20260809T154721Z-super-research\`.
  - One distinct successor code-spec run after accepted synthesis; no implementation surface is writable now.
- `exemplars`:
  - `.orch/runs/20260809T132140Z-search-pareto/synthesis.md` at SHA-256 `BA71FD755898546FC1027BC07C5A9B8264517263721AF37F3819F4CE32A65EC2`: imitate atomic source trace, disagreement/gaps registers, explicit dominance limits, and complete successor delta; reverse its fake-only/live-adapter conclusion where the clarified requirement supplies a required scenario.
  - `.orch/runs/20260809T145250Z-search-pareto-native/spec.md` at SHA-256 `7F9CE10EEF0251488EE75920AA6ABE431BDFB52AF605FD509F04AF8EB6C25A91`: use only as the complete baseline to supersede; preserve its explicit-call, provenance, authority, failure, grouping, and ownership invariants.
- `routing`:
  - `pack`: `orch-research-pack`
- `bound`:
  - Seven blind evidence lanes plus one terminal synthesis.
  - At most 14 retained primary sources and 22 substantive source reads per lane; prefer exact API/source/schema/terms sections over broad marketing pages.
  - Each platform family is covered by one owning lane; cross-family conclusions enter only at synthesis.
  - One adversarial research-lens gate, one combined correction pass, and one terminal verification.
  - `plan_gate`: false; the successor code spec retains `plan_gate: true`.
- `question`: Which platform-specific mechanisms and compliant access paths from Agent Reach, Last30Days, and distinct adjacent tools should an original orchflows super-research skill implement to retrieve timely web, social, community, media, code, feed, post, thread, comment, transcript, engagement, and date evidence more efficiently and transparently than those tools, without importing their skills or scripts?
- `source_policy`: Current official repositories/source, platform API/CLI/feed documentation, terms/security/privacy material, and primary benchmarks through 2026-08-09; pinned commits where available; secondary discovery only; no live credentialed call, login, restricted-content access, or external mutation.
- `rigor_bar`: Every platform/capability/access claim has direct current primary support. Every architectural requirement traces to two independent platform observations or one platform observation plus a canonical orchflows constraint. Missing or restricted access remains a gap or gated adapter, never an asserted bypass. Claimed efficiency names avoided calls/content/model work and a falsifier; claimed quality requires a common workload or remains a design judgment.
- `risks`:
  - Platform APIs, public endpoints, terms, quotas, and page structures drift quickly.
  - Broad platform coverage can recreate a monolith unless the adapter protocol and admission boundary remain strict.
  - Public/search-index fallbacks may omit comments, engagement, deleted items, or precise dates.
  - Authenticated/session routes materially expand custody and prompt-injection risk.
  - Engagement-heavy ordering can amplify popularity bias and shared-upstream duplication.
- `assumptions`:
  - “Everything” means every material source family and mechanism evidenced in the anchors, not an unbounded promise to scrape every website.
  - User-supplied API keys or already-authorized sessions may be supported behind explicit adapters, but secrets are never persisted by the research core.
  - The successor code spec may use approved external CLIs through argv-array adapters when that is the simplest compliant route; it still imports no external skill or script.

## Kind-count decision

Two deliverable kinds: `research` for the current platform/access synthesis and `code` for the successor implementation spec. The runtime composition sequences them so the code spec cites the accepted synthesis identity.
