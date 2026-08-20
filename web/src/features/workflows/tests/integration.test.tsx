import { describe, expect, it } from "vitest";

import { matchCatalog, type RouteLocation } from "../../../app/catalog";
import { featureCatalog } from "../../../app/shell/featureCatalog";

function location(pathname: string, search = ""): RouteLocation {
  return { pathname, search, hash: "" };
}

describe("Workflows application integration", () => {
  it("makes definitions the visible Workflows home while preserving nav-hidden run children", () => {
    const visibleRail = featureCatalog.flatMap((entry) => {
      if (entry.kind === "disabled") return [{ id: entry.id, href: null }];
      if (entry.navigation === false) return [];
      return [{ id: entry.id, href: entry.navigationHref }];
    });

    expect(visibleRail).toEqual([
      { id: "now", href: "/now" },
      { id: "workflows", href: "/workflows" },
      { id: "create", href: null },
      { id: "sessions", href: "/sessions" },
      { id: "friction", href: "/friction" },
    ]);

    expect(matchCatalog(featureCatalog, location("/workflows"))).toMatchObject({
      id: "workflows",
      activeNavigationId: "workflows",
      canonicalHref: "/workflows",
    });
    expect(matchCatalog(featureCatalog, location("/workflows/evolve"))).toMatchObject({
      id: "workflow-detail",
      activeNavigationId: "workflows",
      canonicalHref: "/workflows/evolve",
    });
    expect(matchCatalog(featureCatalog, location("/workflows/evolve/sources/src_campaign"))).toMatchObject({
      id: "workflow-source",
      activeNavigationId: "workflows",
      canonicalHref: "/workflows/evolve/sources/src_campaign",
    });
    expect(matchCatalog(featureCatalog, location("/runs/run-gamma"))).toMatchObject({
      id: "run-map",
      activeNavigationId: "workflows",
    });
    expect(matchCatalog(featureCatalog, location("/runs/run-gamma/tickets/G1"))).toMatchObject({
      id: "ticket",
      activeNavigationId: "workflows",
    });
  });
});
