import type { Edge, Node } from "@xyflow/react";
import { useMemo } from "react";

interface MiniMapNodeData {
  ticket?: { readiness?: { state?: string } };
  group?: { id?: string };
}

export function RunTopologyMiniMap({ nodes, edges }: { nodes: Node[]; edges: Edge[] }) {
  const geometry = useMemo(() => {
    const sized = nodes.map((node) => {
      const width = node.type === "group" ? 280 : 184;
      const height = node.type === "group" ? 108 : 88;
      return { node, width, height };
    });
    const minX = Math.min(...sized.map(({ node }) => node.position.x));
    const minY = Math.min(...sized.map(({ node }) => node.position.y));
    const maxX = Math.max(...sized.map(({ node, width }) => node.position.x + width));
    const maxY = Math.max(...sized.map(({ node, height }) => node.position.y + height));
    const scale = Math.min(156 / Math.max(1, maxX - minX), 72 / Math.max(1, maxY - minY));
    const point = (node: Node, width: number, height: number) => ({
      x: 7 + (node.position.x - minX + width / 2) * scale,
      y: 7 + (node.position.y - minY + height / 2) * scale
    });
    const byId = new Map(sized.map((item) => [item.node.id, { ...item, ...point(item.node, item.width, item.height) }]));
    return { byId, scale, sized };
  }, [nodes]);

  return <svg className="run-map__minimap" viewBox="0 0 170 86" role="img" tabIndex={0}
    aria-label={`Run graph minimap, ${nodes.length} nodes and ${edges.length} dependencies`}>
    <title>Complete visible run topology</title>
    {edges.map((edge) => {
      const source = geometry.byId.get(edge.source);
      const target = geometry.byId.get(edge.target);
      return source && target ? <line key={edge.id} x1={source.x} y1={source.y} x2={target.x} y2={target.y} /> : null;
    })}
    {geometry.sized.map(({ node, width, height }) => {
      const center = geometry.byId.get(node.id)!;
      const data = node.data as MiniMapNodeData;
      return <rect key={node.id} x={center.x - width * geometry.scale / 2} y={center.y - height * geometry.scale / 2}
        width={Math.max(8, width * geometry.scale)} height={Math.max(5, height * geometry.scale)} rx="2"
        data-status={data.ticket?.readiness?.state ?? data.group?.id ?? "unknown"} />;
    })}
  </svg>;
}
