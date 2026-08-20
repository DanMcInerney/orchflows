import { describe, expect, it } from "vitest";
import * as now from "./now";
import * as runMap from "./run-map";

const nowSources = import.meta.glob("./now/**/*.{ts,tsx}", {
  eager: true,
  query: "?raw",
  import: "default",
}) as Record<string, string>;

const runMapSources = import.meta.glob("./run-map/**/*.{ts,tsx}", {
  eager: true,
  query: "?raw",
  import: "default",
}) as Record<string, string>;

describe("feature package boundaries", () => {
  it("closes Now behind the catalog-facing feature contract", async () => {
    expect(Object.keys(now)).toEqual(expect.arrayContaining([
      "route",
      "schema",
      "request",
      "polling",
      "project",
      "data",
      "model",
      "fixtures",
      "styles",
      "loadView",
    ]));
    expect(now.route.match({ pathname: "/now", search: "", hash: "" })).toEqual({ fixture: "" });
    expect(now.route.build({ fixture: "mixed-live" })).toBe("/now?fixture=mixed-live");
    expect(now.request({ fixture: "mixed-live" })).toEqual({ url: "/api/v1/views/now" });
    expect(() => now.schema({ schema: "orchflows.friction.v1", friction: {} })).toThrow();
    expect((await now.loadView()).default).toBeTypeOf("function");

    for (const source of Object.values(nowSources)) {
      expect(source).not.toMatch(/from\s+["'][^"']*(?:\.\.\/\.\.\/(?:api|app|state)|\.\.\/(?:run-map|inspector|sessions|session-graph|friction))[\w\W]*?["']/);
    }
  });

  it("closes run-map behind its route-correlated data contract", async () => {
    expect(Object.keys(runMap)).toEqual(expect.arrayContaining([
      "route", "schema", "request", "polling", "project", "data",
      "model", "fixtures", "styles", "loadView",
    ]));
    const matched = runMap.route.match({ pathname: "/runs/run alpha", search: "?fixture=full-expanded", hash: "" });
    expect(matched).toEqual({ run: "run alpha", fixture: "full-expanded" });
    expect(runMap.route.build(matched!)).toBe("/runs/run%20alpha?fixture=full-expanded");
    expect(runMap.request({ run: "run alpha", fixture: "" })).toEqual({ url: "/api/v1/views/run-map?run=run+alpha" });
    expect(runMap.request({ run: "ignored", fixture: "summary-active" })).toEqual({ url: "/api/v1/views/run-map" });
    expect(() => runMap.schema({ schema: "orchflows.now.v1", runs: [] })).toThrow();
    expect((await runMap.loadView()).default).toBeTypeOf("function");

    for (const source of Object.values(runMapSources)) {
      expect(source).not.toMatch(/from\s+["'][^"']*(?:\.\.\/\.\.\/(?:api|app|state)|\.\.\/(?:now|inspector|sessions|session-graph|friction))[\w\W]*?["']/);
    }
  });
});
