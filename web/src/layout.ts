import type { Node } from "@xyflow/react";

import type { ObserveSnapshot } from "./model";

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

function requestLayout(worker: Worker, snapshot: ObserveSnapshot, timeout: number) {
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
    worker.postMessage({ requestId, nodes: snapshot.nodes, edges: snapshot.edges });
  });
}

export async function layoutSnapshot(snapshot: ObserveSnapshot): Promise<Node[]> {
  const [elk, fallback] = localWorkers();
  let positions: LayoutReply["positions"];
  try {
    positions = await requestLayout(elk, snapshot, 10_000);
  } catch {
    positions = await requestLayout(fallback, snapshot, 1_000);
  }
  return snapshot.nodes.map((node) => ({
    id: node.id,
    type: "observe",
    ariaLabel: `Select ${node.label}`,
    data: { label: node.label, status: node.status },
    position: positions[node.id] ?? { x: 0, y: 0 }
  }));
}
