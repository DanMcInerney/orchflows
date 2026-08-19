import type { Node } from "@xyflow/react";

import type { ObserveSnapshot } from "./model";

interface LayoutReply {
  requestId: number;
  positions: Record<string, { x: number; y: number }>;
}

let fallbackWorker: Worker | undefined;
let elkWorker: Worker | undefined;
let sequence = 0;
const pending = new Map<number, (positions: LayoutReply["positions"]) => void>();

function listen(worker: Worker): Worker {
  worker.addEventListener("message", (event: MessageEvent<LayoutReply>) => {
    pending.get(event.data.requestId)?.(event.data.positions);
    pending.delete(event.data.requestId);
  });
  return worker;
}

function localWorkers(): Worker[] {
  if (!fallbackWorker) {
    fallbackWorker = listen(
      new Worker(new URL("./layout.worker.ts", import.meta.url), { type: "module" })
    );
    elkWorker = listen(
      new Worker(new URL("./elk.worker.ts", import.meta.url), { type: "module" })
    );
  }
  return [fallbackWorker, elkWorker as Worker];
}

export async function layoutSnapshot(snapshot: ObserveSnapshot): Promise<Node[]> {
  const requestId = ++sequence;
  const positions = await new Promise<LayoutReply["positions"]>((resolve) => {
    pending.set(requestId, resolve);
    for (const worker of localWorkers()) {
      worker.postMessage({ requestId, nodes: snapshot.nodes, edges: snapshot.edges });
    }
  });
  return snapshot.nodes.map((node) => ({
    id: node.id,
    ariaLabel: `Select ${node.label}`,
    data: { label: node.label, status: node.status },
    position: positions[node.id] ?? { x: 0, y: 0 }
  }));
}
