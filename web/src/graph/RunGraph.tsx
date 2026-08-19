import { Background, Controls, ReactFlow, ReactFlowProvider, type Edge, type Node } from "@xyflow/react";
import { useEffect, useMemo, useState } from "react";
import type { TicketSummary } from "../api/schema";
import { layoutSnapshot } from "../layout";
import { StatusNode } from "./StatusNode";

const nodeTypes = { status: StatusNode };

export function RunGraph({ tickets }: { tickets: TicketSummary[] }) {
  const fallbackNodes = useMemo<Node[]>(() => tickets.map((ticket, index) => ({
    id: ticket.id,
    type: "status",
    position: { x: 48 + (index % 3) * 280, y: 44 + Math.floor(index / 3) * 152 },
    data: { label: ticket.id, status: ticket.readiness.state, explanation: ticket.readiness.explanation }
  })), [tickets]);
  const ids = new Set(tickets.map((ticket) => ticket.id));
  const edges = useMemo<Edge[]>(() => tickets.flatMap((ticket) => ticket.depends_on
    .filter((dependency) => ids.has(dependency))
    .map((dependency) => ({
      id: `${dependency}->${ticket.id}`,
      source: dependency,
      target: ticket.id,
      ariaLabel: `${dependency} to ${ticket.id}: canonical dependency`
    }))), [tickets]);
  const [laidOutNodes, setLaidOutNodes] = useState<Node[] | null>(null);
  useEffect(() => {
    setLaidOutNodes(null);
    if (typeof Worker === "undefined") return;
    let current = true;
    void layoutSnapshot({
      revision: tickets.map((ticket) => ticket.id).join("\n"),
      active: tickets.some((ticket) => ticket.status === "claimed"),
      nodes: tickets.map((ticket) => ({ id: ticket.id, label: ticket.id, status: ticket.readiness.state })),
      edges: edges.map((edge) => ({ id: edge.id, source: edge.source, target: edge.target }))
    }).then((layout) => {
      if (!current) return;
      const positions = new Map(layout.map((node) => [node.id, node.position]));
      setLaidOutNodes(fallbackNodes.map((node) => ({ ...node, position: positions.get(node.id) ?? node.position })));
    }).catch(() => { /* The worker owns its deterministic fallback; retain the safe grid if both workers fail. */ });
    return () => { current = false; };
  }, [edges, fallbackNodes, tickets]);
  const nodes = laidOutNodes ?? fallbackNodes;
  return (
    <ReactFlowProvider>
      <ReactFlow
        aria-label="Run dependency graph"
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        nodesDraggable={false}
        nodesConnectable={false}
        edgesReconnectable={false}
        deleteKeyCode={null}
        fitView
        minZoom={0.45}
        maxZoom={1.6}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={24} size={1} />
        <Controls showInteractive={false} aria-label="Graph zoom controls" />
      </ReactFlow>
    </ReactFlowProvider>
  );
}
