/// <reference lib="webworker" />

import ELK from "elkjs/lib/elk.bundled.js";

import type { ObserveEdge, ObserveNode } from "./model";

interface LayoutRequest {
  requestId: number;
  nodes: ObserveNode[];
  edges: ObserveEdge[];
}

const elk = new ELK();

self.addEventListener("message", async (event: MessageEvent<LayoutRequest>) => {
  const graph = await elk.layout({
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "RIGHT",
      "elk.spacing.nodeNode": "36",
      "elk.layered.spacing.nodeNodeBetweenLayers": "72"
    },
    children: event.data.nodes.map((node) => ({ id: node.id, width: 180, height: 68 })),
    edges: event.data.edges.map((edge) => ({
      id: edge.id,
      sources: [edge.source],
      targets: [edge.target]
    }))
  });
  const positions = Object.fromEntries(
    (graph.children ?? []).map((node) => [node.id, { x: node.x ?? 0, y: node.y ?? 0 }])
  );
  self.postMessage({ requestId: event.data.requestId, positions });
});
