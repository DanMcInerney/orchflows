// Temporary type-only compatibility for the unmounted legacy graph fixtures.
// Application payload schemas live inside their feature packages.
export type ReadinessState =
  | "waiting"
  | "ready"
  | "running"
  | "attention"
  | "complete"
  | "unknown";

export type ReadinessCause =
  | "pending_dependency"
  | "suspended_handoff"
  | "failed_upstream"
  | "blocked_upstream"
  | "stale_claim"
  | "malformed_topology"
  | "none";

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
