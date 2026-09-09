import { Handle, Position, type Edge, type Node, type NodeProps } from "@xyflow/react";
import { buildTopology, readinessGroups, statusGlyph, type CausalFocus, type ReadinessGroup, type TicketSummary } from "./model";

interface TicketNodeData extends Record<string, unknown> {
  ticket: TicketSummary;
  causal: "focus" | "dimmed" | "off";
}

export interface GroupNodeData extends Record<string, unknown> {
  group: ReadinessGroup;
}

function TicketNode({ data, selected }: NodeProps) {
  const { ticket, causal } = data as TicketNodeData;
  return (
    <article
      className="run-ticket-node"
      data-status={ticket.readiness.state}
      data-causal={causal}
      aria-label={`${ticket.id}, ${ticket.readiness.state}: ${ticket.readiness.explanation}`}
      aria-current={selected ? "true" : undefined}
    >
      <Handle type="target" position={Position.Left} isConnectable={false} aria-hidden="true" />
      <span className="run-ticket-node__glyph" aria-hidden="true">{statusGlyph(ticket.readiness.state)}</span>
      <strong>{ticket.id}</strong>
      <span className="run-ticket-node__state">{ticket.readiness.state}</span>
      <small>{ticket.executor || "executor unavailable"}</small>
      <Handle type="source" position={Position.Right} isConnectable={false} aria-hidden="true" />
    </article>
  );
}

function GroupNode({ data, selected }: NodeProps) {
  const { group } = data as GroupNodeData;
  return (
    <article className="run-group-node" data-status={group.id} aria-current={selected ? "true" : undefined}>
      <Handle type="target" position={Position.Left} isConnectable={false} aria-hidden="true" />
      <span className="run-group-node__glyph" aria-hidden="true">{statusGlyph(group.id)}</span>
      <div><strong>{group.label}</strong><small>{group.ticketIds.length} work items</small></div>
      <span className="run-group-node__ids">{group.ticketIds.join(" · ")}</span>
      <Handle type="source" position={Position.Right} isConnectable={false} aria-hidden="true" />
    </article>
  );
}

export const nodeTypes = { ticket: TicketNode, group: GroupNode };

export function projectedGraph(
  tickets: TicketSummary[],
  expanded: boolean,
  selectedTicket: string,
  selectedGroup: string,
  causal: CausalFocus | null
): { nodes: Node[]; edges: Edge[] } {
  const topology = buildTopology(tickets);
  const focus = new Set(causal?.ticketIds ?? []);
  if (expanded) {
    const indexed = new Map(tickets.map((ticket) => [ticket.id, ticket]));
    const depths = new Map<string, number>();
    function depth(id: string, active = new Set<string>()): number {
      if (topology.diagnostics.some((diagnostic) => diagnostic.kind === "cycle")) return 0;
      const known = depths.get(id);
      if (known !== undefined) return known;
      if (active.has(id)) return 0;
      const ticket = indexed.get(id);
      const next = new Set(active).add(id);
      const value = ticket?.depends_on.length
        ? Math.max(0, ...ticket.depends_on.map((dependency) => depth(dependency, next))) + 1
        : 0;
      depths.set(id, value);
      return value;
    }
    const lanes = new Map<number, number>();
    const nodes: Node[] = tickets.map((ticket, index) => ({
      id: ticket.id,
      type: "ticket",
      position: topology.diagnostics.some((diagnostic) => diagnostic.kind === "cycle")
        ? { x: 56 + (index % 3) * 264, y: 56 + Math.floor(index / 3) * 140 }
        : (() => {
            const column = depth(ticket.id);
            const lane = lanes.get(column) ?? 0;
            lanes.set(column, lane + 1);
            return { x: 40 + column * 204, y: 52 + lane * 120 };
          })(),
      selected: ticket.id === selectedTicket,
      ariaRole: "button",
      ariaLabel: `Open ticket ${ticket.id}`,
      domAttributes: { "aria-pressed": ticket.id === selectedTicket },
      data: {
        ticket,
        causal: causal ? (focus.has(ticket.id) ? "focus" : "dimmed") : "off"
      } satisfies TicketNodeData
    }));
    const missing = [...new Set(topology.edges.filter((edge) => edge.missingSource).map((edge) => edge.source))];
    for (const [index, id] of missing.entries()) nodes.push({
      id,
      type: "ticket",
      focusable: false,
      selectable: false,
      position: { x: 56 + ((tickets.length + index) % 3) * 264, y: 56 + Math.floor((tickets.length + index) / 3) * 140 },
      data: {
        ticket: {
          id,
          status: "missing",
          executor: "",
          bound: "",
          claimed_at: "",
          claimed_by: "",
          depends_on: [],
          unreadable: true,
          readiness: {
            state: "unknown",
            dependencies: [],
            explanation: `${id} is a missing dependency`,
            cause: "malformed_topology",
            causal_chain: [id]
          }
        },
        causal: causal ? (focus.has(id) ? "focus" : "dimmed") : "off"
      } satisfies TicketNodeData
    });
    return {
      nodes,
      edges: topology.edges.map((edge) => {
        const causalId = `${edge.source}->${edge.target}`;
        const isFocus = Boolean(causal?.edgeIds.includes(causalId));
        return {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          type: "straight",
          focusable: true,
          ariaLabel: `${edge.source} is a dependency of ${edge.target}`,
          className: causal ? (isFocus ? "run-edge--focus" : "run-edge--dimmed") : "",
          animated: false
        };
      })
    };
  }

  const groups = readinessGroups(tickets);
  const byTicket = new Map(groups.flatMap((group) => group.ticketIds.map((id) => [id, group.id])));
  const bundles = new Map<string, { source: string; target: string; count: number }>();
  for (const edge of topology.edges) {
    const source = byTicket.get(edge.source);
    const target = byTicket.get(edge.target);
    if (!source || !target || source === target) continue;
    const id = `${source}->${target}`;
    const bundle = bundles.get(id) ?? { source, target, count: 0 };
    bundle.count += 1;
    bundles.set(id, bundle);
  }
  return {
    nodes: groups.map((group, index) => ({
      id: `group:${group.id}`,
      type: "group",
      position: { x: 64 + (index % 2) * 352, y: 68 + Math.floor(index / 2) * 156 },
      selected: group.id === selectedGroup,
      ariaRole: "button",
      ariaLabel: `Open ${group.label} group`,
      domAttributes: { "aria-pressed": group.id === selectedGroup },
      data: { group } satisfies GroupNodeData
    })),
    edges: [...bundles.entries()].map(([id, bundle]) => ({
      id,
      source: `group:${bundle.source}`,
      target: `group:${bundle.target}`,
      label: `${bundle.count}`,
      type: "straight",
      focusable: true,
      ariaLabel: `${bundle.count} dependencies from ${bundle.source} to ${bundle.target}`
    }))
  };
}
