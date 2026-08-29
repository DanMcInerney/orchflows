/// <reference lib="webworker" />

import * as ELKNamespace from "elkjs/lib/elk-api.js";
import ELKEngineWorker from "elkjs/lib/elk-worker.min.js?worker";

import type { ObserveEdge, ObserveNode } from "./model";

interface LayoutRequest {
  requestId: number;
  nodes: ObserveNode[];
  edges: ObserveEdge[];
  direction?: "RIGHT" | "DOWN";
}

interface ElkApi {
  layout(graph: object): Promise<{ children?: Array<{ id: string; x?: number; y?: number }> }>;
}

type ElkConstructor = new (options: { workerFactory: () => Worker }) => ElkApi;

function elkConstructor(value: unknown): ElkConstructor {
  let candidate = value;
  for (let depth = 0; depth < 4; depth += 1) {
    if (typeof candidate === "function") return candidate as ElkConstructor;
    if (!candidate || typeof candidate !== "object" || !("default" in candidate)) break;
    candidate = (candidate as { default: unknown }).default;
  }
  throw new TypeError("ELK API constructor is unavailable");
}

const ELK = elkConstructor(ELKNamespace);
const elk = new ELK({ workerFactory: () => new ELKEngineWorker() });

self.addEventListener("message", async (event: MessageEvent<LayoutRequest>) => {
  const graph = await elk.layout({
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": event.data.direction ?? "RIGHT",
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
