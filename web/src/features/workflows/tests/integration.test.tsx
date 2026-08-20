import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { matchCatalog, type RouteLocation } from "../../../app/catalog";
import { featureCatalog } from "../../../app/shell/featureCatalog";

function location(pathname: string, search = ""): RouteLocation {
  return { pathname, search, hash: "" };
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

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

  it("binds deterministic catalog, topology, and source states through the feature host", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 503 })));

    const catalog = matchCatalog(featureCatalog, location("/workflows", "?fixture=populated"));
    if (catalog === null) throw new Error("expected workflow catalog match");
    const catalogRender = render(<catalog.View />);
    expect(await screen.findByRole("link", { name: "fix" })).toBeTruthy();
    catalogRender.unmount();

    const detail = matchCatalog(featureCatalog, location("/workflows/evolve", "?fixture=complex-loop"));
    if (detail === null) throw new Error("expected workflow detail match");
    const detailRender = render(<detail.View />);
    expect(await screen.findByRole("button", { name: "Select loop 02-campaign loops to 02-campaign" })).toBeTruthy();
    detailRender.unmount();

    const source = matchCatalog(featureCatalog, location(
      "/workflows/evolve/sources/src_campaign",
      "?fixture=missing-source",
    ));
    if (source === null) throw new Error("expected workflow source match");
    render(<source.View />);
    expect(await screen.findByRole("heading", { name: "Source not found" })).toBeTruthy();
  });
});
