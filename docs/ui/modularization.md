# UI modularization

This specification changes ownership before any visual redesign. It makes a complete UI feature statically traceable from reader projection through data loading, routing, and rendering while preserving the approved reader experience.

## Baseline coupling and preserved invariants

PR 74's shell is component-additive, not feature-modular. The registry eagerly discovers views, while navigation, route parsing, the shared `ExperienceSnapshot`, polling, and whole-snapshot handoff remain separate central seams (`web/src/app/registry.ts`, [shell](../../web/src/ObserveApp.tsx), `web/src/state/location.ts`, `web/src/api/schema.ts`, `web/src/api/client.ts`, `web/src/feed.ts`). A feature change therefore crosses browser and reader concerns assigned to different owners ([architecture](../../ARCHITECTURE.md), [rendered UI contract](README.md)). Feature indices are narrow but not uniform: for example, the [session-graph index](../../web/src/features/session-graph/index.ts) also exports `sessionTopology`.

Implementation must replace glob discovery with one explicit static typed catalog. The catalog is the sole architectural owner of display order, rail participation, route matching/building, view loading, and the binding of a route to one feature's data contract. Feature packages supply private implementations the catalog registers: route functions, schema, request and polling policy, projection, model, view, fixtures, styles, and focused tests. Those functions cannot self-register or dispatch. One shared feature-blind transport retains ETag and polling mechanics. Python domain projections split behind the existing `ui_api` facade.

Dependencies are fixed: `shell -> catalog -> feature -> shared`; the shell may also use shared status primitives. Features never import the catalog, shell, or another feature, and shared code never imports a feature.

The persistent **Now / Workflows / Create / Sessions / Friction** rail and the intentionally glanceable Sessions and Friction treatments remain fixed ([platform contract](platform.md), [rendered UI contract](README.md)). Create remains a visible disabled row with an explanation. The local, offline, read-only, privacy-preserving boundary remains fixed. Visual redesign of Now and Workflows is outside this document.

## Typed catalog, routing, and data binding

Define `featureCatalog` in `app/catalog.ts`. Array order is rail/display order only. Each routable row is created with `defineFeature`, which captures its literal identity and correlated route, payload, and model types:

```ts
type FeatureState<M> =
  | { status: "loading"; model: null; error: null }
  | { status: "ready"; model: M; error: null }
  | { status: "stale"; model: M; error: Diagnostic }
  | { status: "error"; model: null; error: Diagnostic };

interface FeatureSpec<K extends ViewId, Route, Payload, Model> {
  kind: "feature";
  id: K;
  matchPriority: number;
  navigation: false | { label: string; home: Route };
  activeNavigationId: RailViewId | null;
  route: { match(location: Location): Route | null; build(route: Route): string };
  data: {
    schema(value: unknown): Payload;
    request(route: Route): RequestSpec;
    polling(model: Model | null): PollingPolicy;
    project(payload: Payload): Model;
  };
  loadView(): Promise<{ default: ComponentType<{ route: Route; state: FeatureState<Model> }> }>;
}

interface DisabledRailEntry<K extends RailViewId> {
  kind: "disabled";
  id: K;
  navigation: { label: string; reason: string };
}
```

The catalog contains `defineFeature(spec)` results plus a `DisabledRailEntry` for Create; the disabled row has no route, data, or loader. `defineFeature<K, Route, Payload, Model>` returns a shell-facing registration whose match result closes over the same `spec` and typed `Route`. That opaque bound match mounts a generated host which invokes the captured loader and feature hook; the route passes only through its captured `request`, `schema`, `project`, `polling`, and `Model` view. A heterogeneous catalog therefore cannot pair one identity with another feature's data, and the shell never handles those type parameters.

For an enabled rail row, the canonical href is `route.build(navigation.home)`. For every match, `route.build(matchedRoute)` is the canonical deep-link href; parse/build round trips are tested and the shell replaces a noncanonical equivalent. A nav-hidden ticket or run-topology row uses `navigation: false` and sets `activeNavigationId` to Now; definition detail and source rows set it to Workflows, and session-topology sets it to Sessions. This preserves parent highlighting without adding rail rows. An enabled row sets it to its own rail identity.

The router evaluates every routable row, selects the highest `matchPriority`, and treats zero matches as the shell's not-found state. Tied highest matches are a catalog-construction error and an admission-test failure. Priority is explicit and independent of array order, so rail reordering cannot alter routing. Duplicate identities and enabled-rail canonical hrefs are also rejected.

This catalog replaces fallback navigation, parent-route exceptions, and route switches ([shell](../../web/src/ObserveApp.tsx), `web/src/state/location.ts`). There is no second registration or routing owner.

## Feature-local frontend boundary

Use these boundaries:

```text
web/src/
  app/{catalog.ts,shell/}
  shared/{tokens/,primitives/,transport/,graph/}
  features/<feature>/
    {index.ts,route.ts,model.ts,fixtures.ts,styles.css}
    data/{schema.ts,request.ts,useFeed.ts}
    view/<Feature>View.tsx
    tests/<feature>.*.test.tsx
```

`index.ts` exports route, data, and loader implementations for registration, but not a second assembled module. The catalog assembles them with identity, order, navigation, active parent, and priority. Feature-local `useFeed(route)` supplies its request, schema, projection, and polling policy to shared `usePollingTransport`; shared transport alone owns HTTP, ETag, abort/generation handling, retry timing, and timers, and knows no feature identity. The shell matches and mounts one bound feature; it never constructs feature requests or models. Only the mounted feature polls.

On first load the view receives `loading`; a first `404`, schema failure, diagnostic, or `5xx` produces `error` with no model. After a valid model, the same failures retain that model as `stale` with a typed non-sensitive diagnostic. A valid later response returns `ready`; `304` preserves the current valid state. Route change aborts or invalidates the old generation so it cannot overwrite the new one. This is the sole shell/feature/transport lifecycle.

Fixtures, styles, views, and focused tests stay beside the model. Small feature-local duplication is preferable to hidden coupling, following the explicit, searchable module rule and locality target ([code craft](../../packs/orch-code-pack/references/craft.md)).

## Backend projection, API, failure, and privacy boundary

[`scripts/ui_api.py`](../../scripts/ui_api.py) remains the public reader facade: it creates the Starlette app, applies host/security policy, and explicitly assembles routes. Domain projection logic moves to `ui_now_projection.py`, `ui_runs_projection.py` (including ticket detail), `ui_workflows_projection.py`, `ui_sessions_projection.py`, and `ui_friction_projection.py`, with typed contracts and no imports between domains. The facade imports each route table and rejects duplicate method/path pairs at startup ([architecture](../../ARCHITECTURE.md)).

All JSON routes use one content-derived ETag/`If-None-Match` helper. Existing `/api/v1/*` and `/api/observe` shapes remain until endpoint parity passes; `/api/v1/experience` is only a compatibility adapter.

A projector validates identifiers, reads only its declared root, and returns a closed schema. It follows the [privacy boundary](platform.md#projection-and-privacy-boundary): redact host paths and never return transcript text, prompts, tool or command output, arbitrary files, or another ticket body. Missing resources are domain-local `404`s; malformed source state becomes a typed non-sensitive diagnostic; unexpected failures become a generic route-local `5xx`. Projectors never mutate state, launch work, or widen containment.

## Tracer-first compatibility migration

Here **tracer** means the repository's thin end-to-end implementation slice, not a feature name ([code craft](../../packs/orch-code-pack/references/craft.md)).

1. Freeze PR 74 behavior: navigation/parent highlighting, canonical and hidden deep links, legacy JSON, ETag/304, retry/stale/error states, and rendered semantics.
2. Add catalog registrations beside current seams, initially adapting existing views and `ExperienceSnapshot`. Transfer one ownership seam only after its parity checks pass.
3. Use **Now** as the first tracer. Register its route, schema, request, polling, projection, model/view, fixtures, styles, and focused tests; move its backend projection to `ui_now_projection.py`; serve the feature route and old endpoint from that projection; and prove response, ETag, route, and rendered parity.
4. Repeat feature by feature while keeping the fixed rail and glanceable Sessions/Friction behavior.
5. After every entry passes parity, remove `ExperienceSnapshot`, glob registration, fallback navigation, the duplicate route parser/switch, parent exceptions, and compatibility adapters used only for whole-snapshot handoff. Completion requires this removal; it is not optional. Endpoint retirement outside that handoff remains separately governed.

## Contributor recipe, tests, and admission

- **Add:** implement feature-local pieces, register one typed catalog row, add its projection behind `ui_api`, and retain a predecessor endpoint until parity passes.
- **Replace:** keep identity and route/data contracts; swap local implementation and fixtures, then run contract and rendered cases.
- **Remove:** first inventory supported links, refresh/parity cases, compatibility consumers, and parent highlighting; migrate or explicitly retire them and prove none still requires the entry. Only then delete the catalog row/package and route, retire its endpoint, and remove its rendered identities.
- **Reorder:** move the catalog row only; explicit match priorities and canonical hrefs remain unchanged.
- **Deep-link:** register a nav-hidden row with priority, canonical parse/build, `activeNavigationId`, refresh coverage, fixtures, and manifest identities.

Test focused feature behavior; catalog identity/type correlation and conflict rejection; facade and old/new projection parity; canonical parse/build, precedence, refresh, disabled Create, and hidden-parent highlighting; lifecycle first-load/stale/recovery behavior; and deterministic fixture rendering.

When rendered inventory changes, update [`view-manifest.json`](view-manifest.json), the expected identity set/count in [`experience_projection.py`](../../tests/test_ui_cases/experience_projection.py), the current-inventory assertion in [`ui_frontend.py`](../../tools/ui_frontend.py), and the [platform inventory contract](platform.md#rendered-experience-admission) in the same owner-reviewed change; then capture, audit, and diff the new inventory.

Admission requires the dependency rules above and the [510-line ceiling](../../tools/check_source_sizes.py). Run `uv run --no-project python -m unittest tests.test_ui_cases.experience_projection -v`, `uv run --no-project python tools/ui_frontend.py verify-build`, `uv run --no-project python tools/ui_frontend.py audit-licenses`, `uv run --no-project python tools/ui_frontend.py smoke --experience`, then every command in [`AGENTS.md`](../../AGENTS.md#required-checks).

Modularization is complete only when catalog-only reordering preserves routing; disabled Create and the fixed rail render correctly; a nav-hidden deep link highlights its parent and survives refresh; lifecycle, parity, routing, fixture, and manifest checks pass; `ExperienceSnapshot` and duplicate nav/router ownership are absent; and all admission commands are green.
