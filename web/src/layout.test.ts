import { afterEach, expect, it, vi } from "vitest";

afterEach(() => {
  vi.resetModules();
  vi.unstubAllGlobals();
});

it("waits for authoritative ELK instead of racing the fallback", async () => {
  const posted: string[] = [];
  class WorkerStub {
    url: string;
    listeners = new Map<string, Set<(event: unknown) => void>>();
    constructor(url: URL) { this.url = url.toString(); }
    addEventListener(name: string, listener: (event: unknown) => void) {
      const listeners = this.listeners.get(name) ?? new Set();
      listeners.add(listener); this.listeners.set(name, listeners);
    }
    removeEventListener(name: string, listener: (event: unknown) => void) {
      this.listeners.get(name)?.delete(listener);
    }
    postMessage(message: { requestId: number }) {
      posted.push(this.url.includes("elk.worker") ? "elk" : "fallback");
      if (this.url.includes("elk.worker")) setTimeout(() => {
        for (const listener of this.listeners.get("message") ?? []) {
          listener({ data: { requestId: message.requestId, positions: { A: { x: 7, y: 9 } } } });
        }
      }, 20);
    }
  }
  vi.stubGlobal("Worker", WorkerStub);
  const { layoutSnapshot } = await import("./layout");
  const nodes = await layoutSnapshot({
    revision: "one", active: true,
    nodes: [{ id: "A", label: "A", status: "claimed" }], edges: []
  });
  expect(posted).toEqual(["elk"]);
  expect(nodes[0].position).toEqual({ x: 7, y: 9 });
  expect(nodes[0].type).toBe("observe");
});

it("lays out an exact generic topology through the authoritative ELK worker", async () => {
  const posted: Array<{ worker: string; message: unknown }> = [];
  class WorkerStub {
    url: string;
    listeners = new Map<string, Set<(event: unknown) => void>>();
    constructor(url: URL) { this.url = url.toString(); }
    addEventListener(name: string, listener: (event: unknown) => void) {
      const listeners = this.listeners.get(name) ?? new Set();
      listeners.add(listener); this.listeners.set(name, listeners);
    }
    removeEventListener(name: string, listener: (event: unknown) => void) {
      this.listeners.get(name)?.delete(listener);
    }
    postMessage(message: { requestId: number }) {
      const worker = this.url.includes("elk.worker") ? "elk" : "fallback";
      posted.push({ worker, message });
      if (worker === "elk") setTimeout(() => {
        for (const listener of this.listeners.get("message") ?? []) {
          listener({ data: { requestId: message.requestId, positions: { A: { x: 11, y: 13 }, B: { x: 97, y: 113 } } } });
        }
      }, 0);
    }
  }
  vi.stubGlobal("Worker", WorkerStub);
  const { layoutTopology } = await import("./layout");
  const positions = await layoutTopology({
    nodes: [{ id: "A" }, { id: "B" }],
    edges: [{ id: "loop-b", source: "B", target: "B" }],
  });

  expect(posted.map(({ worker }) => worker)).toEqual(["elk"]);
  expect(posted[0].message).toMatchObject({
    nodes: [{ id: "A" }, { id: "B" }],
    edges: [{ id: "loop-b", source: "B", target: "B" }],
  });
  expect(positions).toEqual({ A: { x: 11, y: 13 }, B: { x: 97, y: 113 } });
});
