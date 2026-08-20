import { describe, expect, it } from "vitest";
import * as now from "./now";

const nowSources = import.meta.glob("./now/**/*.{ts,tsx}", {
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
});
