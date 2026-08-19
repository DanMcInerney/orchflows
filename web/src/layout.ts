import type { Node } from "@xyflow/react";

import type { ObserveSnapshot } from "./model";

interface LayoutReply {
  requestId: number;
  positions: Record<string, { x: number; y: number }>;
}

let worker: Worker | undefined;
let sequence = 0;
const pending = new Map<number, (positions: LayoutReply["positions"]) => void>();

function localWorker(): Worker {
  if (!worker) {
    worker = new Worker(new URL("./layout.worker.ts", import.meta.url), { type: "module" });
    worker.addEventListener("message", (event: MessageEvent<LayoutReply>) => {
      pending.get(event.data.requestId)?.(event.data.positions);
      pending.delete(event.data.requestId);
    });
  }
  return worker;
}

export async function layoutSnapshot(snapshot: ObserveSnapshot): Promise<Node[]> {
  const requestId = ++sequence;
  const positions = await new Promise<LayoutReply["positions"]>((resolve) => {
    pending.set(requestId, resolve);
    localWorker().postMessage({ requestId, nodes: snapshot.nodes, edges: snapshot.edges });
  });
  return snapshot.nodes.map((node) => ({
    id: node.id,
    ariaLabel: `Select ${node.label}`,
    data: { label: node.label, status: node.status },
    position: positions[node.id] ?? { x: 0, y: 0 }
  }));
}
