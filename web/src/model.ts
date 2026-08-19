export interface ObserveNode {
  id: string;
  label: string;
  status: string;
}

export interface ObserveEdge {
  id: string;
  source: string;
  target: string;
}

export interface ObserveSnapshot {
  revision: string;
  active: boolean;
  nodes: ObserveNode[];
  edges: ObserveEdge[];
}

export function isObserveSnapshot(value: unknown): value is ObserveSnapshot {
  if (!value || typeof value !== "object") return false;
  const record = value as Record<string, unknown>;
  return typeof record.revision === "string"
    && typeof record.active === "boolean"
    && Array.isArray(record.nodes)
    && record.nodes.every((node) => {
      if (!node || typeof node !== "object") return false;
      const candidate = node as Record<string, unknown>;
      return typeof candidate.id === "string"
        && typeof candidate.label === "string"
        && typeof candidate.status === "string";
    })
    && Array.isArray(record.edges)
    && record.edges.every((edge) => {
      if (!edge || typeof edge !== "object") return false;
      const candidate = edge as Record<string, unknown>;
      return typeof candidate.id === "string"
        && typeof candidate.source === "string"
        && typeof candidate.target === "string";
    });
}
