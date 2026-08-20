import { Background, Controls, ReactFlow, ReactFlowProvider, type Edge, type Node, type NodeProps } from "@xyflow/react";
import { useMemo } from "react";
import type { NowTicket } from "./model";

type StatusNode = Node<{ label: string; status: string; explanation: string }, "status">;

function StatusNodeView({ data }: NodeProps<StatusNode>) {
  return <div className="status-node" data-status={data.status} title={data.explanation}>
    <strong>{data.label}</strong><span>{data.status}</span>
  </div>;
}

const nodeTypes = { status: StatusNodeView };

export function RunGraph({ tickets }: { tickets: NowTicket[] }) {
  const nodes = useMemo<StatusNode[]>(() => tickets.map((ticket, index) => ({
    id: ticket.id,
    type: "status",
    position: { x: 48 + (index % 3) * 280, y: 44 + Math.floor(index / 3) * 152 },
    data: { label: ticket.id, status: ticket.readiness.state, explanation: ticket.readiness.explanation },
  })), [tickets]);
  const ids = new Set(tickets.map((ticket) => ticket.id));
  const edges = useMemo<Edge[]>(() => tickets.flatMap((ticket) => ticket.depends_on
    .filter((dependency) => ids.has(dependency))
    .map((dependency) => ({
      id: `${dependency}->${ticket.id}`,
      source: dependency,
      target: ticket.id,
      ariaLabel: `${dependency} to ${ticket.id}: canonical dependency`,
    }))), [ids, tickets]);

  return <ReactFlowProvider><ReactFlow
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
  ><Background gap={24} size={1} /><Controls showInteractive={false} aria-label="Graph zoom controls" /></ReactFlow></ReactFlowProvider>;
}
