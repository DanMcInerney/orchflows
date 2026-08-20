export type ViewId = "now" | "run-map" | "ticket" | "sessions" | "session-graph" | "friction";
export type NavigationId = ViewId | "create";
export type ReadinessState = "waiting" | "ready" | "running" | "attention" | "complete" | "unknown";
export type ReadinessCause =
  | "pending_dependency"
  | "suspended_handoff"
  | "failed_upstream"
  | "blocked_upstream"
  | "stale_claim"
  | "malformed_topology"
  | "none";
export type RunDiagnosticKind = "cycle" | "dangling" | "duplicate" | "unreadable" | "inferred_session_edge";

export interface Readiness {
  state: ReadinessState;
  dependencies: string[];
  explanation: string;
  cause: ReadinessCause;
  causal_chain: string[];
}

export interface TicketSummary {
  id: string;
  status: string;
  executor: string;
  bound: string;
  claimed_at: string;
  claimed_by: string;
  depends_on: string[];
  readiness: Readiness;
  unreadable: boolean;
}

export interface RunDiagnostic { kind: RunDiagnosticKind; ticket_ids: string[]; message: string }
export interface RunSummary {
  id: string;
  ticket_count: number;
  active: boolean;
  objective: string;
  repository: string;
  client: string;
  last_activity: string;
  unreadable: boolean;
  tickets: TicketSummary[];
}
export interface RunDetail {
  id: string;
  active: boolean;
  tickets: TicketSummary[];
  diagnostics: RunDiagnostic[];
  counts: Record<string, number>;
}
export interface TicketHistory { ts: string; event: string; agent: string; detail: string }
export interface TicketDetail extends TicketSummary {
  sections: Record<string, string>;
  verification: { state: string; rows: Array<Record<string, string>> };
  inputs: string[];
  write_scope: string[];
  pack: string;
  history: TicketHistory[];
  raw: string;
}
export interface SessionSummary {
  id: string;
  title: string;
  client: string;
  project: string;
  modified: string;
  agent_count: number;
  diagnostics: string[];
}
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
export interface FrictionItem {
  ts?: string;
  host?: string;
  observed?: string;
  expected?: string;
  run?: string;
  ticket?: string;
}
export interface NavigationItem {
  id: NavigationId;
  label: string;
  path: string;
  disabled: boolean;
  explanation: string;
}

export interface ExperienceSnapshot {
  schema: "orchflows.experience.v1";
  navigation: NavigationItem[];
  selection: { view: ViewId; run: string; ticket: string; session: string };
  runs: RunSummary[];
  run: RunDetail | null;
  ticket: TicketDetail | null;
  sessions: { items: SessionSummary[]; diagnostics: string[]; empty: boolean };
  session: SessionDetail | null;
  friction: { items: FrictionItem[]; skipped: number; unreadable: number };
}

function object(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object";
}

export function isExperienceSnapshot(value: unknown): value is ExperienceSnapshot {
  if (!object(value) || value.schema !== "orchflows.experience.v1") return false;
  if (!Array.isArray(value.navigation) || !Array.isArray(value.runs)) return false;
  if (!object(value.selection) || typeof value.selection.view !== "string") return false;
  if (value.run !== null && (!object(value.run) || !Array.isArray(value.run.tickets))) return false;
  return object(value.sessions) && object(value.friction);
}
