import type { Node } from "@xyflow/react";

import type { ObserveSnapshot } from "./model";

export interface TopologyLayoutInput {
  nodes: Array<{ id: string }>;
  edges: Array<{ id: string; source: string; target: string }>;
  direction?: "RIGHT" | "DOWN";
}

interface LayoutReply {
  requestId: number;
  positions: Record<string, { x: number; y: number }>;
}

let fallbackWorker: Worker | undefined;
let elkWorker: Worker | undefined;
let sequence = 0;

function localWorkers(): [Worker, Worker] {
  if (!fallbackWorker) {
    fallbackWorker = new Worker(new URL("./layout.worker.ts", import.meta.url), { type: "module" });
    elkWorker = new Worker(new URL("./elk.worker.ts", import.meta.url), { type: "module" });
  }
  return [elkWorker as Worker, fallbackWorker];
}

function requestLayout(worker: Worker, topology: TopologyLayoutInput, timeout: number) {
  const requestId = ++sequence;
  return new Promise<LayoutReply["positions"]>((resolve, reject) => {
    const cleanup = () => {
      window.clearTimeout(timer);
      worker.removeEventListener("message", reply);
      worker.removeEventListener("error", failed);
    };
    const reply = (event: MessageEvent<LayoutReply>) => {
      if (event.data.requestId !== requestId) return;
      cleanup();
      resolve(event.data.positions);
    };
    const failed = () => { cleanup(); reject(new Error("layout worker failed")); };
    const timer = window.setTimeout(failed, timeout);
    worker.addEventListener("message", reply);
    worker.addEventListener("error", failed);
    worker.postMessage({ requestId, nodes: topology.nodes, edges: topology.edges, direction: topology.direction });
  });
}

export async function layoutTopology(topology: TopologyLayoutInput): Promise<LayoutReply["positions"]> {
  const [elk, fallback] = localWorkers();
  try {
    return await requestLayout(elk, topology, 10_000);
  } catch {
    return requestLayout(fallback, topology, 1_000);
  }
}

export async function layoutSnapshot(snapshot: ObserveSnapshot): Promise<Node[]> {
  const positions = await layoutTopology(snapshot);
  return snapshot.nodes.map((node) => ({
    id: node.id,
    type: "observe",
    ariaLabel: `Select ${node.label}`,
    data: { label: node.label, status: node.status },
    position: positions[node.id] ?? { x: 0, y: 0 }
  }));
}
