import { createElement } from "react";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  CatalogError,
  defineCatalog,
  defineFeature,
  featureCatalog,
  matchCatalog,
  type FeatureSpec,
  type RouteLocation,
} from "./catalog";

type ItemRoute = { item: string };
type ItemPayload = { value: number };
type ItemModel = { label: string };

function itemFeature(
  id: "workflow-detail" | "workflow-source",
  matchPriority: number,
  home: ItemRoute = { item: id },
) {
  return defineFeature<"workflow-detail" | "workflow-source", ItemRoute, ItemPayload, ItemModel>({
    kind: "feature",
    id,
    matchPriority,
    navigation: { label: id, home },
    activeNavigationId: "workflows",
    route: {
      match(location) {
        const match = /^\/items\/([^/]+)\/?$/.exec(location.pathname);
        return match ? { item: decodeURIComponent(match[1]) } : null;
      },
      build(route) {
        return `/items/${encodeURIComponent(route.item)}`;
      },
    },
    data: {
      schema(value) {
        if (!value || typeof value !== "object" || typeof (value as ItemPayload).value !== "number") {
          throw new Error("invalid payload");
        }
        return value as ItemPayload;
      },
      request(route) {
        return { url: `/api/items/${encodeURIComponent(route.item)}` };
      },
      polling: () => false,
      project: (payload) => ({ label: String(payload.value) }),
    },
    loadView: async () => ({
      default: ({ route, state }) => createElement(
        "div",
        null,
        `${route.item}:${state.status}:${state.model?.label ?? ""}`,
      ),
    }),
  });
}

function location(pathname: string): RouteLocation {
  return { pathname, search: "", hash: "" };
}

function catalogErrorCode(run: () => unknown): string | undefined {
  try {
    run();
    return undefined;
  } catch (error) {
    return error instanceof CatalogError ? error.code : undefined;
  }
}

describe("feature catalog", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("rejects duplicate identities and duplicate enabled canonical hrefs", () => {
    expect(catalogErrorCode(() => defineCatalog([
      itemFeature("workflow-detail", 10),
      itemFeature("workflow-detail", 20),
    ]))).toBe("duplicate-id");

    expect(catalogErrorCode(() => defineCatalog([
      itemFeature("workflow-detail", 10, { item: "shared" }),
      itemFeature("workflow-source", 20, { item: "shared" }),
    ]))).toBe("duplicate-href");
  });

  it("keeps generic catalog validation feature-blind", () => {
    const workflowDetail = itemFeature("workflow-detail", 10);
    const runMap = { ...workflowDetail, id: "run-map" as const };

    expect(defineCatalog([runMap])).toEqual([runMap]);
  });

  it("owns the complete application route and navigation catalog literally", () => {
    expect(featureCatalog.map((entry) => entry.id)).toEqual([
      "now",
      "workflows",
      "run-map",
      "workflow-detail",
      "workflow-source",
      "ticket",
      "create",
      "sessions",
      "session-graph",
      "friction",
    ]);

    const visibleRail = featureCatalog.flatMap((entry) => {
      if (entry.kind === "disabled") return [entry.navigation.label];
      return entry.navigation === false ? [] : [entry.navigation.label];
    });
    expect(visibleRail).toEqual(["Now", "Workflows", "Create", "Sessions", "Friction"]);
  });

  it("assigns execution descendants to Now and definition descendants to Workflows", () => {
    expect(matchCatalog(featureCatalog, location("/runs/run-alpha"))).toMatchObject({
      id: "run-map",
      activeNavigationId: "now",
    });
    expect(matchCatalog(featureCatalog, location("/runs/run-alpha/tickets/T-1"))).toMatchObject({
      id: "ticket",
      activeNavigationId: "now",
    });
    expect(matchCatalog(featureCatalog, location("/workflows/evolve"))).toMatchObject({
      id: "workflow-detail",
      activeNavigationId: "workflows",
    });
    expect(matchCatalog(featureCatalog, location("/workflows/evolve/sources/src_campaign"))).toMatchObject({
      id: "workflow-source",
      activeNavigationId: "workflows",
    });
  });

  it("rejects noncanonical and non-round-tripping navigation homes", () => {
    const invalid = {
      ...itemFeature("workflow-detail", 10),
      navigationHref: "https://example.test/items/alpha",
    };
    expect(catalogErrorCode(() => defineCatalog([invalid]))).toBe("invalid-canonical-href");

    const spec: FeatureSpec<"workflow-detail", ItemRoute, ItemPayload, ItemModel> = {
      kind: "feature",
      id: "workflow-detail",
      matchPriority: 10,
      navigation: { label: "Alpha", home: { item: "alpha" } },
      activeNavigationId: "workflows",
      route: { match: () => null, build: ({ item }) => `/items/${item}` },
      data: {
        schema: (value) => value as ItemPayload,
        request: () => ({ url: "/api/items" }),
        polling: () => false,
        project: ({ value }) => ({ label: String(value) }),
      },
      loadView: async () => ({ default: () => null }),
    };
    expect(catalogErrorCode(() => defineFeature(spec))).toBe("invalid-home-route");
  });

  it("uses priority rather than catalog order and reports canonical deep links", () => {
    const low = itemFeature("workflow-detail", 10);
    const high = itemFeature("workflow-source", 20);
    const forward = matchCatalog(defineCatalog([low, high]), location("/items/a%20b/"));
    const reversed = matchCatalog(defineCatalog([high, low]), location("/items/a%20b/"));

    expect(forward?.id).toBe("workflow-source");
    expect(reversed?.id).toBe("workflow-source");
    expect(forward).toMatchObject({ canonicalHref: "/items/a%20b", isCanonical: false });
  });

  it("rejects tied highest-priority route matches", () => {
    const catalog = defineCatalog([
      itemFeature("workflow-detail", 10),
      itemFeature("workflow-source", 10),
    ]);
    expect(catalogErrorCode(() => matchCatalog(catalog, location("/items/shared")))).toBe("tied-match");
  });

  it("returns a bound view that keeps route, payload, and model handling inside the registration", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(200, { value: 7 })));
    const match = matchCatalog(
      defineCatalog([itemFeature("workflow-detail", 10, { item: "home" })]),
      location("/items/bound"),
    );
    if (match === null) throw new Error("expected a route match");

    render(createElement(match.View));

    expect(await screen.findByText("bound:ready:7")).toBeTruthy();
  });
});

function response(status: number, value: unknown): Response {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

// This function is never called; pnpm typecheck proves the catalog keeps a
// feature's route, payload, and model types correlated at its definition.
function correlationTypeChecks() {
  defineFeature<"workflow-detail", ItemRoute, ItemPayload, ItemModel>({
    kind: "feature",
    id: "workflow-detail",
    matchPriority: 1,
    navigation: false,
    activeNavigationId: "workflows",
    route: { match: () => null, build: ({ item }) => `/items/${item}` },
    data: {
      schema: (value) => value as ItemPayload,
      // @ts-expect-error A request cannot receive another feature's route type.
      request: (route: { page: number }) => ({ url: `/api/${route.page}` }),
      polling: () => false,
      project: ({ value }) => ({ label: String(value) }),
    },
    loadView: async () => ({ default: () => null }),
  });
}

void correlationTypeChecks;
