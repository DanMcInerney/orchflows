import {
  Suspense,
  createElement,
  lazy,
  type ComponentType,
} from "react";
import * as friction from "../features/friction";
import * as inspector from "../features/inspector";
import * as now from "../features/now";
import * as runMap from "../features/run-map";
import * as sessionGraph from "../features/session-graph";
import * as sessions from "../features/sessions";
import * as workflows from "../features/workflows";
import { usePollingTransport } from "../shared/transport";
import type {
  FeatureData,
  FeatureState,
} from "../shared/transport/types";

export type RailViewId = "now" | "workflows" | "create" | "sessions" | "friction";
export type ViewId =
  | RailViewId
  | "run-map"
  | "ticket"
  | "session-graph"
  | "workflow-detail"
  | "workflow-source";

export interface RouteLocation {
  pathname: string;
  search: string;
  hash: string;
}

export interface FeatureSpec<K extends ViewId, Route, Payload, Model> {
  kind: "feature";
  id: K;
  matchPriority: number;
  navigation: false | { label: string; home: Route };
  activeNavigationId: RailViewId | null;
  route: {
    match(location: RouteLocation): Route | null;
    build(route: Route): string;
  };
  data: FeatureData<Route, Payload, Model>;
  loadView(): Promise<{
    default: ComponentType<{ route: Route; state: FeatureState<Model> }>;
  }>;
}

export interface FeatureMatch<K extends ViewId = ViewId> {
  id: K;
  activeNavigationId: RailViewId | null;
  matchPriority: number;
  canonicalHref: string;
  isCanonical: boolean;
  View: ComponentType;
}

export interface FeatureRegistration<K extends ViewId = ViewId> {
  kind: "feature";
  id: K;
  matchPriority: number;
  navigation: false | { label: string };
  navigationHref: string | null;
  activeNavigationId: RailViewId | null;
  match(location: RouteLocation): FeatureMatch<K> | null;
}

export interface DisabledRailEntry<K extends RailViewId = RailViewId> {
  kind: "disabled";
  id: K;
  navigation: { label: string; reason: string };
}

export type CatalogEntry = FeatureRegistration | DisabledRailEntry;

export class CatalogError extends Error {
  constructor(
    readonly code:
      | "duplicate-id"
      | "duplicate-href"
      | "invalid-canonical-href"
      | "invalid-home-route"
      | "tied-match",
    message: string,
  ) {
    super(message);
    this.name = "CatalogError";
  }
}

function routeLocation(href: string): RouteLocation {
  const url = new URL(href, "https://reader.invalid");
  return { pathname: url.pathname, search: url.search, hash: url.hash };
}

function validateCanonicalHref(href: string): void {
  if (!href.startsWith("/") || href.startsWith("//")) {
    throw new CatalogError("invalid-canonical-href", `Catalog href must be root-relative: ${href}`);
  }
  const url = new URL(href, "https://reader.invalid");
  if (`${url.pathname}${url.search}${url.hash}` !== href) {
    throw new CatalogError("invalid-canonical-href", `Catalog href is not canonical: ${href}`);
  }
}

export function defineFeature<K extends ViewId, Route, Payload, Model>(
  spec: FeatureSpec<K, Route, Payload, Model>,
): FeatureRegistration<K> {
  const FeatureView = lazy(spec.loadView);
  const navigationHref = spec.navigation === false ? null : spec.route.build(spec.navigation.home);
  if (navigationHref !== null) {
    validateCanonicalHref(navigationHref);
    const matchedHome = spec.route.match(routeLocation(navigationHref));
    if (matchedHome === null || spec.route.build(matchedHome) !== navigationHref) {
      throw new CatalogError("invalid-home-route", `Navigation home does not round trip: ${spec.id}`);
    }
  }

  return {
    kind: "feature",
    id: spec.id,
    matchPriority: spec.matchPriority,
    navigation: spec.navigation === false ? false : { label: spec.navigation.label },
    navigationHref,
    activeNavigationId: spec.activeNavigationId,
    match(location) {
      const route = spec.route.match(location);
      if (route === null) return null;
      const canonicalHref = spec.route.build(route);
      validateCanonicalHref(canonicalHref);
      const BoundView = () => {
        const state = usePollingTransport(route, spec.data);
        return createElement(
          Suspense,
          { fallback: null },
          createElement(FeatureView, { route, state }),
        );
      };
      return {
        id: spec.id,
        activeNavigationId: spec.activeNavigationId,
        matchPriority: spec.matchPriority,
        canonicalHref,
        isCanonical: `${location.pathname}${location.search}${location.hash}` === canonicalHref,
        View: BoundView,
      };
    },
  };
}

export function defineCatalog<const Entries extends readonly CatalogEntry[]>(
  entries: Entries,
): readonly CatalogEntry[] {
  const identities = new Set<string>();
  const hrefs = new Set<string>();
  for (const entry of entries) {
    if (identities.has(entry.id)) {
      throw new CatalogError("duplicate-id", `Duplicate catalog identity: ${entry.id}`);
    }
    identities.add(entry.id);
    if (entry.kind === "feature" && entry.navigationHref !== null) {
      validateCanonicalHref(entry.navigationHref);
      if (hrefs.has(entry.navigationHref)) {
        throw new CatalogError("duplicate-href", `Duplicate navigation href: ${entry.navigationHref}`);
      }
      hrefs.add(entry.navigationHref);
    }
  }
  return Object.freeze([...entries]);
}

export const featureCatalog = defineCatalog([
  defineFeature({
    kind: "feature",
    id: "now",
    matchPriority: 10,
    navigation: { label: "Now", home: { fixture: "" } },
    activeNavigationId: "now",
    route: now.route,
    data: now.data,
    loadView: now.loadView,
  }),
  defineFeature({
    kind: "feature",
    id: "workflows",
    matchPriority: 10,
    navigation: { label: "Workflows", home: { fixture: "" } },
    activeNavigationId: "workflows",
    route: workflows.list.route,
    data: workflows.list.data,
    loadView: workflows.list.loadView,
  }),
  defineFeature({
    kind: "feature",
    id: "run-map",
    matchPriority: 10,
    navigation: false,
    activeNavigationId: "workflows",
    route: runMap.route,
    data: runMap.data,
    loadView: runMap.loadView,
  }),
  defineFeature({
    kind: "feature",
    id: "workflow-detail",
    matchPriority: 20,
    navigation: false,
    activeNavigationId: "workflows",
    route: workflows.detail.route,
    data: workflows.detail.data,
    loadView: workflows.detail.loadView,
  }),
  defineFeature({
    kind: "feature",
    id: "workflow-source",
    matchPriority: 30,
    navigation: false,
    activeNavigationId: "workflows",
    route: workflows.source.route,
    data: workflows.source.data,
    loadView: workflows.source.loadView,
  }),
  defineFeature({
    kind: "feature",
    id: "ticket",
    matchPriority: 20,
    navigation: false,
    activeNavigationId: "workflows",
    route: inspector.route,
    data: inspector.data,
    loadView: inspector.loadView,
  }),
  {
    kind: "disabled",
    id: "create",
    navigation: {
      label: "Create",
      reason: "Future workflow authoring is unavailable in this read-only observer.",
    },
  },
  defineFeature({
    kind: "feature",
    id: "sessions",
    matchPriority: 10,
    navigation: { label: "Sessions", home: { fixture: "" } },
    activeNavigationId: "sessions",
    route: sessions.route,
    data: sessions.data,
    loadView: sessions.loadView,
  }),
  defineFeature({
    kind: "feature",
    id: "session-graph",
    matchPriority: 20,
    navigation: false,
    activeNavigationId: "sessions",
    route: sessionGraph.route,
    data: sessionGraph.data,
    loadView: sessionGraph.loadView,
  }),
  defineFeature({
    kind: "feature",
    id: "friction",
    matchPriority: 10,
    navigation: { label: "Friction", home: { fixture: "" } },
    activeNavigationId: "friction",
    route: friction.route,
    data: friction.data,
    loadView: friction.loadView,
  }),
] as const);

export function matchCatalog(
  catalog: readonly CatalogEntry[],
  location: RouteLocation,
): FeatureMatch | null {
  const matches = catalog.flatMap((entry) => {
    if (entry.kind === "disabled") return [];
    const match = entry.match(location);
    return match === null ? [] : [match];
  });
  if (matches.length === 0) return null;
  const highestPriority = Math.max(...matches.map((match) => match.matchPriority));
  const highest = matches.filter((match) => match.matchPriority === highestPriority);
  if (highest.length > 1) {
    throw new CatalogError(
      "tied-match",
      `Tied catalog route match: ${highest.map((match) => match.id).join(", ")}`,
    );
  }
  return highest[0];
}
