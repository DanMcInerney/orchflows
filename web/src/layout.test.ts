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
