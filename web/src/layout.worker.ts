/// <reference lib="webworker" />

import type { ObserveNode } from "./model";

interface LayoutRequest {
  requestId: number;
  nodes: ObserveNode[];
}

self.addEventListener("message", (event: MessageEvent<LayoutRequest>) => {
  const positions = Object.fromEntries(
    event.data.nodes.map((node, index) => [node.id, { x: index * 252, y: 0 }])
  );
  setTimeout(() => self.postMessage({ requestId: event.data.requestId, positions }), 150);
});
