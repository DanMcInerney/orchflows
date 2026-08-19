import type { Readiness, ReadinessCause, ReadinessState, TicketSummary } from "../../api/schema";

export type RunMapFilter = "active" | "problems" | "ready" | "critical" | "all";
export type DiagnosticKind = "cycle" | "dangling" | "duplicate" | "unreadable" | "inferred";
export type CauseKind = "pending" | "suspended" | "failed" | "stale" | "malformed" | "none";
export type CanonicalCause = ReadinessCause;

export type CanonicalCausalReadiness = Pick<Readiness, "cause" | "causal_chain">;

export interface CanonicalEdge {
  id: string;
  source: string;
  target: string;
  missingSource: boolean;
}

export interface TopologyDiagnostic {
  id: string;
  kind: DiagnosticKind;
  ticketIds: string[];
  message: string;
}

export interface TopologyModel {
  tickets: TicketSummary[];
  edges: CanonicalEdge[];
  diagnostics: TopologyDiagnostic[];
  criticalPath: string[];
}

export interface CausalFocus {
  ticketIds: string[];
  edgeIds: string[];
  kind: CauseKind;
  summary: string;
  evidence: string;
}

export interface ReadinessGroup {
  id: ReadinessState;
  label: string;
  ticketIds: string[];
  statuses: string[];
}

const GROUP_LABEL: Record<ReadinessState, string> = {
  attention: "Needs attention",
  running: "Running",
  ready: "Ready now",
  waiting: "Waiting",
  complete: "Verified complete",
  unknown: "Unknown"
};

const GROUP_ORDER: ReadinessState[] = ["attention", "running", "ready", "waiting", "complete", "unknown"];

function comparePath(left: string[], right: string[]): number {
  if (left.length !== right.length) return right.length - left.length;
  return left.join("\u0000").localeCompare(right.join("\u0000"));
}

function criticalPath(tickets: TicketSummary[]): string[] {
  const ids = new Set(tickets.map((ticket) => ticket.id));
  const dependencies = new Map(tickets.map((ticket) => [
    ticket.id,
    [...ticket.depends_on].filter((dependency) => ids.has(dependency)).sort()
  ]));
  const memo = new Map<string, string[]>();

  function visit(id: string, stack: Set<string>): string[] {
    const known = memo.get(id);
    if (known) return known;
    if (stack.has(id)) return [];
    const nextStack = new Set(stack).add(id);
    const candidates = (dependencies.get(id) ?? []).map((dependency) => visit(dependency, nextStack));
    candidates.sort(comparePath);
    const path = [...(candidates[0] ?? []), id];
    memo.set(id, path);
    return path;
  }

  return tickets.map((ticket) => visit(ticket.id, new Set())).sort(comparePath)[0] ?? [];
}

function cycleDiagnostics(tickets: TicketSummary[]): TopologyDiagnostic[] {
  const dependencies = new Map<string, string[]>();
  for (const ticket of tickets) {
    dependencies.set(ticket.id, [...new Set([...(dependencies.get(ticket.id) ?? []), ...ticket.depends_on])]);
  }
  const visited = new Set<string>();
  const active = new Set<string>();
  const stack: string[] = [];
  const found = new Map<string, string[]>();

  function visit(id: string) {
    if (active.has(id)) {
      const start = stack.indexOf(id);
      const cycle = [...stack.slice(start), id];
      const key = [...new Set(cycle)].sort().join("|");
      found.set(key, cycle);
      return;
    }
    if (visited.has(id) || !dependencies.has(id)) return;
    visited.add(id);
    active.add(id);
    stack.push(id);
    for (const dependency of dependencies.get(id) ?? []) visit(dependency);
    stack.pop();
    active.delete(id);
  }

  for (const id of [...dependencies.keys()].sort()) visit(id);
  return [...found.entries()].sort(([left], [right]) => left.localeCompare(right)).map(([key, cycle]) => ({
    id: `cycle:${key}`,
    kind: "cycle",
    ticketIds: [...new Set(cycle)],
    message: `Dependency cycle: ${cycle.join(" → ")}`
  }));
}

export function buildTopology(tickets: TicketSummary[]): TopologyModel {
  const seen = new Map<string, number>();
  for (const ticket of tickets) seen.set(ticket.id, (seen.get(ticket.id) ?? 0) + 1);
  const ids = new Set(seen.keys());
  const edges = tickets.flatMap((ticket) => ticket.depends_on.map((dependency, index) => ({
    id: `${dependency}->${ticket.id}:${index}`,
    source: dependency,
    target: ticket.id,
    missingSource: !ids.has(dependency)
  })));
  const diagnostics: TopologyDiagnostic[] = [];

  for (const [id, count] of [...seen.entries()].sort(([left], [right]) => left.localeCompare(right))) {
    if (count > 1) diagnostics.push({
      id: `duplicate:${id}`,
      kind: "duplicate",
      ticketIds: [id],
      message: `Duplicate ticket id ${id} appears ${count} times.`
    });
  }
  for (const edge of edges.filter((candidate) => candidate.missingSource)) diagnostics.push({
    id: `dangling:${edge.id}`,
    kind: "dangling",
    ticketIds: [edge.source, edge.target],
    message: `${edge.target} depends on missing ticket ${edge.source}.`
  });
  for (const ticket of tickets.filter((candidate) => candidate.unreadable)) diagnostics.push({
    id: `unreadable:${ticket.id}`,
    kind: "unreadable",
    ticketIds: [ticket.id],
    message: `${ticket.id} could not be read completely.`
  });
  for (const ticket of tickets) {
    const inferred = (ticket as TicketSummary & { inferred_session_edges?: string[] }).inferred_session_edges;
    for (const session of inferred ?? []) diagnostics.push({
      id: `inferred:${session}->${ticket.id}`,
      kind: "inferred",
      ticketIds: [ticket.id],
      message: `Inferred session link ${session} → ${ticket.id}; not a canonical dependency.`
    });
  }
  diagnostics.push(...cycleDiagnostics(tickets));
  return { tickets, edges, diagnostics, criticalPath: criticalPath(tickets) };
}

export function readinessGroups(tickets: TicketSummary[]): ReadinessGroup[] {
  return GROUP_ORDER.map((state) => {
    const members = tickets.filter((ticket) => ticket.readiness.state === state);
    return {
      id: state,
      label: GROUP_LABEL[state],
      ticketIds: members.map((ticket) => ticket.id),
      statuses: [...new Set(members.map((ticket) => ticket.status))].sort()
    };
  }).filter((group) => group.ticketIds.length > 0);
}

export function filterTickets(
  tickets: TicketSummary[],
  filter: RunMapFilter,
  query: string,
  path: string[]
): TicketSummary[] {
  const normalized = query.trim().toLocaleLowerCase();
  const critical = new Set(path);
  return tickets.filter((ticket) => {
    const searchMatches = !normalized || `${ticket.id} ${ticket.executor}`.toLocaleLowerCase().includes(normalized);
    const filterMatches = filter === "all"
      || (filter === "active" && ticket.readiness.state === "running")
      || (filter === "problems" && (ticket.readiness.state === "attention" || ticket.readiness.state === "unknown" || ticket.unreadable))
      || (filter === "ready" && ticket.readiness.state === "ready")
      || (filter === "critical" && critical.has(ticket.id));
    return searchMatches && filterMatches;
  });
}

function classifyCause(cause: CanonicalCause): CauseKind {
  if (cause === "suspended_handoff") return "suspended";
  if (cause === "failed_upstream" || cause === "blocked_upstream") return "failed";
  if (cause === "stale_claim") return "stale";
  if (cause === "malformed_topology") return "malformed";
  if (cause === "pending_dependency") return "pending";
  return "none";
}

function causeSummary(kind: CauseKind, ticket: TicketSummary | undefined): string {
  const id = ticket?.id ?? "a missing dependency";
  if (kind === "suspended") return `Waiting on suspended handoff ${id}.`;
  if (kind === "failed") return `Waiting on failed or blocked upstream work ${id}.`;
  if (kind === "stale") return `Waiting on stale claim ${id}.`;
  if (kind === "malformed") return `Waiting cannot be resolved because ${id} is malformed.`;
  if (kind === "pending") return `Waiting on pending dependency ${id}.`;
  return "No authoritative blocking chain is projected for this ticket.";
}

export function authoritativeCausalFocus(ticketId: string, tickets: TicketSummary[]): CausalFocus {
  const indexed = new Map(tickets.map((ticket) => [ticket.id, ticket]));
  const selected = indexed.get(ticketId);
  if (!selected) return {
    ticketIds: [],
    edgeIds: [],
    kind: "malformed",
    summary: causeSummary("malformed", undefined),
    evidence: "Selected ticket is absent from the canonical graph."
  };
  const kind = classifyCause(selected.readiness.cause);
  const chain = selected.readiness.causal_chain;
  const blocker = indexed.get(chain.at(-1) ?? "");
  if (kind === "none" || chain.length < 2) return {
    ticketIds: selected ? [selected.id] : [],
    edgeIds: [],
    kind,
    summary: causeSummary(kind, selected),
    evidence: selected.readiness.explanation
  };
  return {
    ticketIds: chain,
    edgeIds: chain.slice(1).map((id, index) => `${id}->${chain[index]}`),
    kind,
    summary: causeSummary(kind, blocker),
    evidence: selected.readiness.explanation
  };
}
