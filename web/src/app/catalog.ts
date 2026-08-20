import {
  Suspense,
  createElement,
  lazy,
  type ComponentType,
} from "react";
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
): Readonly<Entries> {
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
  return Object.freeze([...entries]) as unknown as Readonly<Entries>;
}

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
