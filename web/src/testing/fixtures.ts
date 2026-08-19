export const fixtureCopy: Record<string, { eyebrow: string; title: string; note: string }> = {
  "mixed-live": { eyebrow: "Live overview", title: "Work is moving across three runs", note: "Canonical status remains the source of truth." },
  "needs-attention": { eyebrow: "Needs attention", title: "One blocked dependency needs a decision", note: "Causal explanations name the exact dependency." },
  "no-active-runs": { eyebrow: "All quiet", title: "No active runs", note: "Completed and waiting history remains available." },
  "unreadable-data": { eyebrow: "Reader diagnostic", title: "Some state could not be read", note: "Unreadable records stay explicit and contained." },
  "live-paused": { eyebrow: "Live paused", title: "Automatic refresh is paused", note: "The last safe snapshot remains visible." }
};

export function fixtureText(state: string) {
  return fixtureCopy[state] ?? {
    eyebrow: "Deterministic fixture",
    title: state ? state.replaceAll("-", " ") : "Observe",
    note: "This foundation identity is reserved for its feature view."
  };
}

function ticket(id: string, status: string, state: ReadinessState, depends_on: string[], explanation: string): TicketSummary {
  return {
    id, status, executor: "orch-render", bound: "90m", claimed_at: "", claimed_by: "",
    depends_on, unreadable: false, readiness: { state, dependencies: [], explanation }
  };
}

export function fixtureTickets(state: string): TicketSummary[] {
  if (state === "empty" || state === "no-active-runs") return [];
  const complete = state === "completed" || state === "proof-pass";
  const attention = ["needs-attention", "proof-fail", "friction-present", "diagnostic", "unreadable-data", "blocked-causal", "malformed-topology"].includes(state);
  const tickets = [
    ticket("00-spec", "complete", "complete", [], "00-spec is complete"),
    ticket("01-foundation", complete ? "complete" : "claimed", complete ? "complete" : "running", ["00-spec"], complete ? "01-foundation is complete" : "01-foundation is claimed"),
    ticket("02-verify", complete ? "complete" : "pending", complete ? "complete" : "waiting", ["01-foundation"], complete ? "02-verify is complete" : "02-verify waits for 01-foundation")
  ];
  if (attention) tickets.push(ticket("03-attention", "blocked", "attention", ["00-spec"], "03-attention needs a decision"));
  return tickets;
}
import type { ReadinessState, TicketSummary } from "../api/schema";
