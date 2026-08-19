import { Background, Controls, ReactFlow, ReactFlowProvider, type Edge, type Node } from "@xyflow/react";
import { useMemo } from "react";
import type { TicketSummary } from "../api/schema";
import { StatusNode } from "./StatusNode";

const nodeTypes = { status: StatusNode };

export function RunGraph({ tickets }: { tickets: TicketSummary[] }) {
  const nodes = useMemo<Node[]>(() => tickets.map((ticket, index) => ({
    id: ticket.id,
    type: "status",
    position: { x: 48 + (index % 3) * 280, y: 44 + Math.floor(index / 3) * 152 },
    data: { label: ticket.id, status: ticket.readiness.state, explanation: ticket.readiness.explanation }
  })), [tickets]);
  const ids = new Set(tickets.map((ticket) => ticket.id));
  const edges = useMemo<Edge[]>(() => tickets.flatMap((ticket) => ticket.depends_on
    .filter((dependency) => ids.has(dependency))
    .map((dependency) => ({ id: `${dependency}->${ticket.id}`, source: dependency, target: ticket.id }))), [tickets]);
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
