import { describe, expect, it } from "vitest";
import { matchCatalog } from "../catalog";
import { featureCatalog } from "./featureCatalog";

function location(pathname: string, search = "") {
  return { pathname, search, hash: "" };
}

describe("application feature catalog", () => {
  it("fixes rail order and binds canonical hidden routes to their parent", () => {
    const rail = featureCatalog.flatMap((entry) => {
      if (entry.kind === "disabled") return [entry.navigation.label];
      return entry.navigation === false ? [] : [entry.navigation.label];
    });

    expect(rail).toEqual(["Now", "Workflows", "Create", "Sessions", "Friction"]);
    expect(featureCatalog.find((entry) => entry.id === "create")).toMatchObject({
      kind: "disabled",
      navigation: { label: "Create" },
    });

    expect(matchCatalog(featureCatalog, location("/runs/run%20alpha/tickets/T-1/"))).toMatchObject({
      id: "ticket",
      activeNavigationId: "workflows",
      canonicalHref: "/runs/run%20alpha/tickets/T-1",
      isCanonical: false,
    });
    expect(matchCatalog(featureCatalog, location("/sessions/session%20alpha"))).toMatchObject({
      id: "session-graph",
      activeNavigationId: "sessions",
      canonicalHref: "/sessions/session%20alpha",
      isCanonical: true,
    });
  });
});
