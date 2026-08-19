export type ViewId = "now" | "run-map" | "ticket" | "sessions" | "session-graph" | "friction";
export type NavigationId = ViewId | "create";
export type ReadinessState = "waiting" | "ready" | "running" | "attention" | "complete" | "unknown";

export interface Readiness {
  state: ReadinessState;
  dependencies: string[];
  explanation: string;
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

export interface RunSummary { id: string; ticket_count: number; active: boolean }
export interface RunDetail { id: string; active: boolean; tickets: TicketSummary[]; counts: Record<string, number> }
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
  ticket: (TicketSummary & {
    sections: Record<string, string>;
    verification: { state: string; rows: Array<Record<string, string>> };
  }) | null;
  sessions: { items: unknown[]; diagnostics: string[]; empty: boolean };
  session: unknown | null;
  friction: { items: unknown[]; skipped: number; unreadable: number };
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
