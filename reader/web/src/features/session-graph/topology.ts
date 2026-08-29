export interface SessionAgent {
  id: string;
  type: string;
  depth: number | null;
  parent: string;
  modified: string;
  state: string;
  evidence: string;
  unreadable: boolean;
}

export interface SessionDetail {
  id: string;
  title: string;
  modified: string;
  agent_count: number;
  diagnostics: string[];
  agents: SessionAgent[];
}

export interface SessionGraphModel {
  session: SessionDetail | null;
}

export type ConnectionProvenance =
  | "session root"
  | "spawn depth 1"
  | "recorded parent"
  | "inferred: no parent recorded"
  | "inferred: recorded parent unresolved";

export interface TopologyNode {
  id: string;
  kind: "session" | "agent";
  label: string;
  type: string;
  depth: number;
  state: string;
  evidence: string;
  modified: string;
  unreadable: boolean;
}

export interface TopologyEdge {
  id: string;
  source: string;
  target: string;
  provenance: ConnectionProvenance;
  inferred: boolean;
}

export interface SessionTopology {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  diagnostics: string[];
}

const SESSION_NODE_ID = "session-root";

function normalizedAgentId(value: string): string {
  return value.startsWith("agent-") ? value.slice("agent-".length) : value;
}

function resolvedParent(parent: string, agent: SessionAgent, agents: SessionAgent[]): string {
  if (!parent) return "";
  const normalized = normalizedAgentId(parent);
  const match = agents.find((candidate) => (
    candidate.id !== agent.id && normalizedAgentId(candidate.id) === normalized
  ));
  return match?.id ?? "";
}

function edgeFor(agent: SessionAgent, agents: SessionAgent[]): TopologyEdge {
  const parent = resolvedParent(agent.parent, agent, agents);
  if (parent) {
    return {
      id: `${parent}->${agent.id}`,
      source: parent,
      target: agent.id,
      provenance: "recorded parent",
      inferred: false
    };
  }
  if (agent.parent) {
    return {
      id: `${SESSION_NODE_ID}->${agent.id}`,
      source: SESSION_NODE_ID,
      target: agent.id,
      provenance: "inferred: recorded parent unresolved",
      inferred: true
    };
  }
  if (agent.depth === 1) {
    return {
      id: `${SESSION_NODE_ID}->${agent.id}`,
      source: SESSION_NODE_ID,
      target: agent.id,
      provenance: "spawn depth 1",
      inferred: false
    };
  }
  return {
    id: `${SESSION_NODE_ID}->${agent.id}`,
    source: SESSION_NODE_ID,
    target: agent.id,
    provenance: "inferred: no parent recorded",
    inferred: true
  };
}

export function sessionTopology(session: SessionDetail): SessionTopology {
  const root: TopologyNode = {
    id: SESSION_NODE_ID,
    kind: "session",
    label: "Orchestrator",
    type: "session",
    depth: 0,
    state: session.agents.some((agent) => agent.state === "running") ? "running" : "unknown",
    evidence: `${session.agent_count} recorded subagents`,
    modified: session.modified,
    unreadable: false
  };
  const nodes = session.agents.map<TopologyNode>((agent) => ({
    id: agent.id,
    kind: "agent",
    label: agent.id,
    type: agent.type || "unknown type",
    depth: agent.depth ?? 0,
    state: agent.unreadable ? "unknown" : (agent.state || "unknown"),
    evidence: agent.unreadable ? "metadata unreadable" : (agent.evidence || "no activity evidence"),
    modified: agent.modified,
    unreadable: agent.unreadable
  }));
  const edges = session.agents.map((agent) => edgeFor(agent, session.agents));
  const inferred = edges.filter((edge) => edge.inferred);
  const diagnostics = [...session.diagnostics];
  if (inferred.some((edge) => edge.provenance === "inferred: recorded parent unresolved")) {
    diagnostics.push("A recorded parent could not be resolved; its edge is inferred to the orchestrator.");
  }
  if (inferred.some((edge) => edge.provenance === "inferred: no parent recorded")) {
    diagnostics.push("A parent was not recorded; its dashed edge is inferred to the orchestrator.");
  }
  if (session.agents.some((agent) => agent.unreadable)) {
    diagnostics.push("Unreadable subagent metadata remains unknown.");
  }
  return { nodes: [root, ...nodes], edges, diagnostics };
}

export function isSessionDetail(value: unknown): value is SessionDetail {
  if (!value || typeof value !== "object") return false;
  const session = value as Record<string, unknown>;
  return typeof session.id === "string"
    && typeof session.title === "string"
    && typeof session.modified === "string"
    && typeof session.agent_count === "number"
    && Array.isArray(session.diagnostics)
    && session.diagnostics.every((item) => typeof item === "string")
    && Array.isArray(session.agents)
    && session.agents.every((item) => {
      if (!item || typeof item !== "object") return false;
      const agent = item as Record<string, unknown>;
      return typeof agent.id === "string"
        && typeof agent.type === "string"
        && (typeof agent.depth === "number" || agent.depth === null)
        && typeof agent.parent === "string"
        && typeof agent.modified === "string"
        && typeof agent.state === "string"
        && typeof agent.evidence === "string"
        && typeof agent.unreadable === "boolean";
    });
}

export { SESSION_NODE_ID };

export const model = { sessionTopology, isSessionDetail };
