# Workflows

`/workflows` is a glanceable vertical catalog of canonical T3 compositions and T1 workflow skills, leading through exact derived detail and contained source inspection to feature-local implementation and executable admission. It keeps composition instances on run routes while preserving the existing shell, Now, Sessions, Friction, and deep-link behavior.

## Catalog experience

Each catalog row uses its canonical owner `name` as stable ID, labels its vocabulary type, and presents that name as a descriptive native link beside source-derived when-use copy and a validated, noninteractive semantic summary. A [T3 composition is a named workflow; a T1 workflow is an assembled, domain-blind skill](../vocabulary.md#structure). Composition entry modes come from their manifests (`routed` or `named`); a T1 workflow's trigger is its callable skill name. The UI does not author identity or when-use copy.

### T3 compositions

- [fix](../../compositions/fix/template.md) — `routed`; any bug or defect with unknown or unverified cause.
- [benchmaker](../../compositions/benchmaker/template.md) — `named`; build and qualify a runnable benchmark.
- [evolve](../../compositions/evolve/template.md) — `named`; run bounded candidate generations against a frozen evaluation; manual only.
- [drift-canary](../../compositions/drift-canary/template.md) — `named`; detect drift after a model, effort, or host change.
- [renovate](../../compositions/renovate/template.md) — `named`; improve a workspace without a user-supplied spec.
- [self-improve](../../compositions/self-improve/template.md) — `named`; turn friction and run evidence into one qualified, landed proposal.
- [skill-tournament](../../compositions/skill-tournament/template.md) — `named`; evolve one skill against its prequalified benchmark.

### T1 workflow skills

- [orch-build](../../skills/workflows/orch-build/SKILL.md) — use for any new or amended skill, pack, or contract.
- [orch-eval-design](../../skills/workflows/orch-eval-design/SKILL.md) — use before benchmark construction or direct judged scoring.
- [orch-fixture](../../skills/workflows/orch-fixture/SKILL.md) — use when a proven ticket should guard against drift.
- [orch-repair](../../skills/workflows/orch-repair/SKILL.md) — use inside a gate or for any accepted defect set.
- [orch-self-improve](../../skills/workflows/orch-self-improve/SKILL.md) — use as the mining stub, or alone when proposals suffice.
- [orch-spec](../../skills/workflows/orch-spec/SKILL.md) — use before any delivery run.
- [orch-triage](../../skills/workflows/orch-triage/SKILL.md) — use before queued items are dispatched.

## Catalog projection and semantic summaries

The catalog is one semantic list whose sole UI-authored metadata is `workflow-summary-manifest.json`; admission proves complete catalog-key coverage, unique valid nodes, valid typed endpoints, bounded labels, and correct loop/cycle semantics. Wide rows place identity and when-use copy beside the compact flow; compact rows stack the same content above a full-width flow. Order and content do not change between the breakpoints in the [rendered-view manifest](view-manifest.json).

Each `<li>` begins with `T3 composition` or `T1 workflow skill`, then the linked canonical name and its when-use copy. Link text names its destination; generic “open” or “details” text is forbidden. The copy remains in the same list item, giving context consistent with [WCAG 2.2 link purpose](https://www.w3.org/WAI/WCAG22/Understanding/link-purpose-in-context.html). The adjacent flow uses labeled nodes and directed connectors to communicate semantic sequence, branching, and repetition. It has no controls and makes no claim to be exact topology. Its nonvisual equivalent is an ordered list: node items in manifest order say `Step: {label}`, followed by edge items in manifest order saying `{source label} continues to | branches to | loops to {target label}`. Connectors are hidden from assistive technology and the visible flow references that list.

`docs/ui/workflow-summary-manifest.json` is the only UI-authored owner of compact flows, within the platform's [read-only projection boundary](platform.md#projection-and-privacy-boundary). Its root is `{schema, workflows}`. `workflows` is keyed by stable catalog ID; each value contains only `nodes: [{id, label}]` and `edges: [{source, target, kind}]`, where `kind` is `sequence`, `branch`, or `loop`. Identity, type, entry, description, membership, and detail topology remain canonical projections.

Validation requires manifest keys to equal the catalog IDs. It rejects duplicate or malformed node IDs; blank, untrimmed, multiline, or longer-than-40-character labels; unknown edge endpoints or kinds; a directed cycle without a `loop` edge; or a `loop` edge that is not part of a cycle.

## Exact derived detail and contained source inspection

Each detail is an exact graph derived mechanically from composition manifests/work stubs or T1 call structure; it preserves typed edges, gives every resolvable node a linkable opaque source ID, and confines redacted reads to an exhaustive allowlist—never a request path. Both graph and ordered relation table use descriptive links; every graph operation is keyboard reachable ([React Flow accessibility](https://reactflow.dev/learn/advanced-use/accessibility)).

`GET /api/v1/workflows` returns exactly `{schema:"orchflows.workflow-catalog.v1",workflows:[{id,type,entry,description,summary}]}`; `type` is `composition | workflow-skill`, `entry` is `routed | named | callable`, and `summary` has the manifest's closed `nodes` and `edges`. `GET /api/v1/workflows/{workflowId}` returns exactly `{schema:"orchflows.workflow-detail.v1",id,type,nodes,edges,relations,diagnostics}`. Nodes are `{id,kind,label,source_id?}`, with `kind` in `workflow | work | skill | script`; edges are `{id,kind,from,to,label}`, with `kind` in `dependency | executor | skill-call | script-call | loop`. `relations` contains exactly one `{id,kind,from,to,label}` per edge, sorted by `from,kind,to,id`; `diagnostics` is sorted by `code,subject_id` and contains `{code,subject_id,message}`, with code in `duplicate-node | dangling-edge | unresolved-reference`. Unknown fields fail schema validation.

Catalog IDs are canonical owner names. Node IDs are `workflow:{workflow}`, `work:{workflow}/{stub}`, `skill:{canonical-name}`, or `script:{normalized-installed-relative-path}`. Edge IDs are `edge:{kind}:{from}:{to}` after percent-encoding components; repeated call occurrences with the same tuple coalesce, so prose position cannot move identity. A source ID is `src_` plus unpadded base64url SHA-256 of the normalized installed-library-relative path; consumers treat every ID as opaque.

For a T3 composition, project its manifest and work stubs: create `work:<workflow>/<stub>` for each stub; add `x -> stub` as `dependency` for every `depends_on: [x]`; add `stub -> skill:<executor>` as `executor`. Do not repair source. Report duplicate nodes, missing dependencies, and unknown executors with closed diagnostic codes `duplicate-node`, `dangling-edge`, and `unresolved-reference`.

For a T1 workflow skill, create the `workflow:{workflow}` caller from its `SKILL.md`; for each validated resolved backticked workflow-skill reference create its `skill:` target and one caller-to-target `skill-call`, and for each validated invoked `.py` command create its `script:` target and one caller-to-target `script-call`. Repeated occurrences coalesce by edge ID. Prose mentions and T0 carriage create nothing. A stub executed by `orch-loop` also receives a `loop` self-edge with its declared bound; its prose does not become a call edge. Thus `evolve` is `00-eval -> 01-eligibility -> 02-campaign -> 03-result`, with four executor edges and one loop on `02-campaign`. That loop names its owned generation sequence—write candidates, submit each fixed evidence result to eligibility, score the incumbent and eligible candidates blind, then select under the frozen rule—without invented iteration nodes ([campaign stub](../../compositions/evolve/02-campaign.md); [generation mapping](../../compositions/references/evolve-generation.md)).

`/workflows/{workflowId}/sources/{sourceId}` and `/api/v1/workflows/{workflowId}/sources/{sourceId}` accept only URL-safe opaque source IDs associated with that workflow. The expected inventory is exactly the composition template, every work stub, every executor skill, and every resolved referenced skill or invoked script; for T1 it is the root `SKILL.md` plus every resolved target. Validation requires inventory equality, a `source_id` on every resolvable node, and a source link for every such ID; unresolved targets instead require `unresolved-reference`. `ui_workflows_projection.py`, assembled by the existing facade, maps each ID to one allowlisted installed-library-relative file, resolves symlinks, proves containment before opening, and reads once ([privacy boundary](platform.md#projection-and-privacy-boundary); [backend boundary](modularization.md#backend-projection-api-failure-and-privacy-boundary)). Success is exactly `{schema:"orchflows.workflow-source.v1",id,text,sha256,language,redacted}`; `sha256` covers delivered UTF-8 text after host-path redaction. Requests never accept paths; responses never expose paths, state-sink data, or unrelated files. Unknown or escaped IDs return generic `404`, unreadable or malformed cataloged sources return non-sensitive typed `422`, and unexpected faults return route-local generic `500`. Success retains shared content-derived ETag/`304` behavior.

## Responsive interaction, navigation, and states

Canonical list/detail/source routes retain native-link, Back, refresh, breadcrumb, and Workflows-parent behavior; wide and compact layouts keep DOM/focus order, expose keyboard and nonvisual graph equivalents, and define populated, empty, unreadable, complex-loop, missing-source, and unreadable-source outcomes. Workflows remains inside the fixed **Now / Workflows / Create / Sessions / Friction** shell. Canonical routes are `/workflows`, `/workflows/{workflowId}`, and `/workflows/{workflowId}/sources/{sourceId}`; builders encode both opaque IDs. Detail and source keep Workflows active. Existing `/runs/{run}` and `/runs/{run}/tickets/{ticket}` remain supported, nav-hidden Workflows children under the [typed-catalog contract](modularization.md#typed-catalog-routing-and-data-binding), not definition aliases. Native anchors preserve open-in-new-tab, copy-link, Back, and refresh. Breadcrumbs link `Workflows / {workflow} / {source}`; source pages also show `Back to {workflow}`.

Wide detail pages place graph and persistent inspector side by side. Compact pages put the selected inspector before the graph, make filters horizontally scrollable, and follow the [run-map responsive precedent](../../web/src/features/run-map/run-map.css). DOM and navigation order agree. Buttons are only filters or disclosures; disclosures expose `aria-expanded` and toggle with Enter or Space ([disclosure pattern](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/)). Tab traverses graph nodes and edges; Enter or Space selects the focused item.

The semantic companion lists every node and labeled edge from the same projection and remains usable when layout fails or density is high. Empty views explain that no definitions are available. Unreadable definitions keep identity, show a non-sensitive diagnostic, and invent no topology. Complex loops retain labeled cyclic edges and are enumerated in the companion. Source views render closed metadata and inert text; missing or unreadable content leaves breadcrumbs and the parent link operable.

## Feature and projection boundaries

One typed `featureCatalog` binding owns route/payload/model correlation; `web/src/features/workflows/` owns the feature-local frontend, `ui_workflows_projection.py` owns its closed backend projections, and dependencies remain `shell -> catalog -> workflows -> shared` and `ui_api -> projector -> canonical owners/shared readers`. The [typed catalog](modularization.md#typed-catalog-routing-and-data-binding) solely owns display order, navigation, match priority, canonical URL construction, and view/data binding. Detail and source select Workflows as their active parent.

`web/src/features/workflows/` owns route, model, data schema/request/polling, fixtures, styles, view, and tests under the [feature-local boundary](modularization.md#feature-local-frontend-boundary). Its model discriminates T3 composition from T1 workflow skill. The summary manifest owns only compact semantic nodes and edges; canonical owners supply exact identity, copy, topology, and source inventory. The shared `ExperienceSnapshot` schema (`web/src/api/schema.ts`) is a compatibility seam, not another Workflows contract.

`scripts/ui_workflows_projection.py` owns the closed catalog, detail, and source projections described above. [`ui_api`](modularization.md#backend-projection-api-failure-and-privacy-boundary) assembles their routes and retains security, ETag, and failure policy. Frontend dependency direction is `shell -> catalog -> workflows -> shared`; shared transport owns HTTP, ETag, retry, timers, and generation invalidation without feature knowledge. Backend direction is `ui_api -> ui_workflows_projection -> canonical owners/shared readers`; domain projectors do not import one another.

## Migration, validation, and admission

Introduce the catalog additively and remove run rows only after focused contract, containment, routing, rendered, and accessibility tests prove the fixed rail and sibling/deep-link parity; executable admission then closes every schema, manifest, reference, and preservation obligation. Specifically, Now still assigns each eligible run once to ordered **Needs attention / Active now / Recently completed** bands and preserves pause/selection/filter context across polling; Sessions keeps its native-link metadata index, labelled filter, and populated/empty/diagnostic states; Friction keeps unreadable/skipped counts, its closed read-only record feed, exact run/ticket links, and empty state. The rail remains **Now / Workflows / Create / Sessions / Friction** with disabled Create. Nav-hidden `/runs/{run}` and `/runs/{run}/tickets/{ticket}` still refresh and highlight Workflows. Then remove run-instance rows only from Workflows; keep their routes and projections ([migration contract](modularization.md#tracer-first-compatibility-migration); current routes (`web/src/state/location.ts`)).

Make three validators admission prerequisites. Summary validation enforces stable-ID coverage and endpoints. Detail validation reconstructs composition and workflow-skill edges, preserves kinds, and requires explicit loops. Source validation enforces cataloged opaque IDs, contained installed-library-relative paths, closed text/hash/language metadata, and rejection of state-sink, arbitrary, or host paths. Keep them behind the reader facade and closed schemas ([facade](../../scripts/ui_api.py); schema (`web/src/api/schema.ts`)).

Focused tests cover all four schema contracts; summary, topology, relation ordering, diagnostic codes, and source-inventory equality; source-ID containment; canonical routing; refresh and parent highlighting for preserved deep links; Now band/context parity; Sessions link/filter/state parity; Friction count/link/empty parity; and rendered wide/compact, keyboard, focus, and accessible-name behavior. Update the [rendered inventory](view-manifest.json) in the same change.

Admission requires zero run instances in `/workflows`, valid workflow and graph references, passing preserved views and routes, and accessibility-clean captures for every manifest identity. Against a running local reader, run:

```text
uv run --no-project python tools/ui_frontend.py verify-build
uv run --no-project python tools/ui_frontend.py audit-licenses
uv run --no-project python tools/ui_frontend.py smoke --experience
uv run --no-project python tools/ui_frontend.py audit --port 8765 --manifest docs/ui/view-manifest.json
```

Also run every repository [required check](../../AGENTS.md#required-checks).
