import { describe, expect, it } from "vitest";
import * as now from "./now";
import * as runMap from "./run-map";
import * as inspector from "./inspector";
import * as sessions from "./sessions";
import * as sessionGraph from "./session-graph";

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

const inspectorSources = import.meta.glob("./inspector/**/*.{ts,tsx}", {
  eager: true,
  query: "?raw",
  import: "default",
}) as Record<string, string>;

const sessionsSources = import.meta.glob("./sessions/**/*.{ts,tsx}", {
  eager: true,
  query: "?raw",
  import: "default",
}) as Record<string, string>;

const sessionGraphSources = import.meta.glob("./session-graph/**/*.{ts,tsx}", {
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
    expect(runMap.request({ run: "fixture-run", fixture: "summary-active" })).toEqual({ url: "/api/v1/views/run-map?run=fixture-run" });
    expect(() => runMap.schema({ schema: "orchflows.now.v1", runs: [] })).toThrow();
    expect((await runMap.loadView()).default).toBeTypeOf("function");

    for (const source of Object.values(runMapSources)) {
      expect(source).not.toMatch(/from\s+["'][^"']*(?:\.\.\/\.\.\/(?:api|app|state)|\.\.\/(?:now|inspector|sessions|session-graph|friction))[\w\W]*?["']/);
    }
  });

  it("closes inspector behind its ticket-correlated data contract", async () => {
    expect(Object.keys(inspector)).toEqual(expect.arrayContaining([
      "route", "schema", "request", "polling", "project", "data",
      "model", "fixtures", "styles", "loadView",
    ]));
    const matched = inspector.route.match({ pathname: "/runs/run%20alpha/tickets/T%2F1", search: "?fixture=proof-pass", hash: "" });
    expect(matched).toEqual({ run: "run alpha", ticket: "T/1", fixture: "proof-pass" });
    expect(inspector.route.build(matched!)).toBe("/runs/run%20alpha/tickets/T%2F1?fixture=proof-pass");
    expect(inspector.request({ run: "run alpha", ticket: "T/1", fixture: "" })).toEqual({
      url: "/api/v1/views/inspector?run=run+alpha&ticket=T%2F1",
    });
    expect(inspector.request({ run: "fixture-run", ticket: "fixture-ticket", fixture: "proof-pass" })).toEqual({
      url: "/api/v1/views/inspector?run=fixture-run&ticket=fixture-ticket",
    });
    expect(() => inspector.schema({ schema: "orchflows.session-graph.v1", session: null })).toThrow();
    expect((await inspector.loadView()).default).toBeTypeOf("function");

    for (const source of Object.values(inspectorSources)) {
      expect(source).not.toMatch(/from\s+["'][^"']*(?:\.\.\/\.\.\/(?:api|app|state)|\.\.\/(?:now|run-map|sessions|session-graph|friction))[\w\W]*?["']/);
    }
  });

  it("closes sessions behind its index data contract", async () => {
    expect(Object.keys(sessions)).toEqual(expect.arrayContaining([
      "route", "schema", "request", "polling", "project", "data",
      "model", "fixtures", "styles", "loadView",
    ]));
    const matched = sessions.route.match({ pathname: "/sessions/", search: "?fixture=populated", hash: "" });
    expect(matched).toEqual({ fixture: "populated" });
    expect(sessions.route.build(matched!)).toBe("/sessions?fixture=populated");
    expect(sessions.request({ fixture: "populated" })).toEqual({ url: "/api/v1/views/sessions" });
    expect(() => sessions.schema({ schema: "orchflows.inspector.v1", run: null, ticket: null })).toThrow();
    expect((await sessions.loadView()).default).toBeTypeOf("function");

    for (const source of Object.values(sessionsSources)) {
      expect(source).not.toMatch(/from\s+["'][^"']*(?:\.\.\/\.\.\/(?:api|app|state)|\.\.\/(?:now|run-map|inspector|session-graph|friction))[\w\W]*?["']/);
    }
  });

  it("closes session-graph behind its session-correlated data contract", async () => {
    expect(Object.keys(sessionGraph)).toEqual(expect.arrayContaining([
      "route", "schema", "request", "polling", "project", "data",
      "model", "fixtures", "styles", "loadView",
    ]));
    const matched = sessionGraph.route.match({ pathname: "/sessions/session%20alpha", search: "?fixture=diagnostic", hash: "" });
    expect(matched).toEqual({ session: "session alpha", fixture: "diagnostic" });
    expect(sessionGraph.route.build(matched!)).toBe("/sessions/session%20alpha?fixture=diagnostic");
    expect(sessionGraph.request({ session: "session alpha", fixture: "diagnostic" })).toEqual({
      url: "/api/v1/views/session-graph?session=session+alpha",
    });
    expect(() => sessionGraph.schema({ schema: "orchflows.sessions.v1", sessions: {} })).toThrow();
    expect((await sessionGraph.loadView()).default).toBeTypeOf("function");

    for (const source of Object.values(sessionGraphSources)) {
      expect(source).not.toMatch(/from\s+["'][^"']*(?:\.\.\/\.\.\/(?:api|app|state)|\.\.\/(?:now|run-map|inspector|sessions|friction))[\w\W]*?["']/);
    }
  });
});
