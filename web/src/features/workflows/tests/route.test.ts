import { describe, expect, it } from "vitest";
import {
  detailRoute,
  listRoute,
  sourceRoute,
} from "../route";

const location = (pathname: string, search = "", hash = "") => ({
  pathname,
  search,
  hash,
});

describe("workflow routes", () => {
  it("round-trips the canonical list route and its fixture query", () => {
    expect(listRoute.match(location("/workflows"))).toEqual({ fixture: "" });
    expect(listRoute.match(location("/workflows/", "?fixture=empty"))).toEqual({
      fixture: "empty",
    });
    expect(listRoute.build({ fixture: "complex loop" })).toBe(
      "/workflows?fixture=complex+loop",
    );
  });

  it("round-trips encoded opaque workflow and source identities", () => {
    const workflowId = "owner/name ?#%";
    const sourceId = "src_a/b ?#%";

    const detailHref = detailRoute.build({ workflowId, fixture: "detail empty" });
    expect(detailHref).toBe(
      "/workflows/owner%2Fname%20%3F%23%25?fixture=detail+empty",
    );
    expect(detailRoute.match(location(
      "/workflows/owner%2Fname%20%3F%23%25",
      "?fixture=detail+empty",
    ))).toEqual({ workflowId, fixture: "detail empty" });

    const sourceHref = sourceRoute.build({ workflowId, sourceId, fixture: "source unreadable" });
    expect(sourceHref).toBe(
      "/workflows/owner%2Fname%20%3F%23%25/sources/src_a%2Fb%20%3F%23%25?fixture=source+unreadable",
    );
    expect(sourceRoute.match(location(
      "/workflows/owner%2Fname%20%3F%23%25/sources/src_a%2Fb%20%3F%23%25",
      "?fixture=source+unreadable",
    ))).toEqual({ workflowId, sourceId, fixture: "source unreadable" });
  });

  it("rejects malformed, empty, and noncanonical path shapes", () => {
    expect(detailRoute.match(location("/workflows"))).toBeNull();
    expect(detailRoute.match(location("/workflows/evolve/extra"))).toBeNull();
    expect(sourceRoute.match(location("/workflows/evolve/sources"))).toBeNull();
    expect(sourceRoute.match(location("/workflows/evolve/sources/src_a/extra"))).toBeNull();
    expect(detailRoute.match(location("/workflows/%"))).toBeNull();
    expect(detailRoute.match(location("/workflows/%65volve"))).toBeNull();
    expect(sourceRoute.match(location("/workflows/evolve/sources/%73rc_a"))).toBeNull();
  });
});
