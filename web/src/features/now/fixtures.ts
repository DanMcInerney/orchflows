import type { ReadinessState } from "../../api/schema";
import type { NowRun, NowTicket } from "./model";

function ticket(id: string, status: string, state: ReadinessState, depends_on: string[], title: string): NowTicket {
  return {
    id, title, status, executor: "orch-render", bound: "90m", claimed_at: "", claimed_by: "",
    depends_on, unreadable: false, readiness: {
      state, dependencies: depends_on, explanation: `${id} is ${state}`,
      cause: state === "attention" ? "blocked_upstream" : state === "waiting" ? "pending_dependency" : "none",
      causal_chain: depends_on,
    },
  };
}

function activeRun(): NowRun {
  return {
    id: "20260819-ui-experience",
    objective: "Make live workflow progress legible without exposing conversation content",
    repository: "orchflows-public · codex/ui-experience",
    client: "Codex desktop",
    lastActivity: "18 seconds ago",
    tickets: [
      ticket("00-brief", "complete", "complete", [], "Settle product decisions"),
      ticket("01-foundation", "complete", "complete", ["00-brief"], "Build the observer substrate"),
      ticket("02-now", "claimed", "running", ["01-foundation"], "Render the live fleet"),
      ticket("03-workflows", "claimed", "running", ["01-foundation"], "Render dependency maps"),
      ticket("04-sessions", "ready", "ready", ["01-foundation"], "Render session structure"),
      ticket("05-review", "pending", "waiting", ["02-now", "03-workflows", "04-sessions"], "Critique the experience"),
      ticket("06-verify", "pending", "waiting", ["05-review"], "Verify deterministic evidence"),
    ],
  };
}

function attentionRun(unreadable = false): NowRun {
  const tickets = [
    ticket("00-scope", "complete", "complete", [], "Confirm the compatibility boundary"),
    ticket("01-repair", unreadable ? "sideways" : "blocked", unreadable ? "unknown" : "attention", ["00-scope"], "Repair the portability seam"),
    ticket("02-check", "pending", "waiting", ["01-repair"], "Re-run compatibility checks"),
  ];
  if (unreadable) tickets[1].unreadable = true;
  return {
    id: unreadable ? "unreadable-run" : "20260819-portability-repair",
    objective: unreadable ? "Run metadata could not be safely projected" : "Restore installed-reader portability across supported hosts",
    repository: unreadable ? "Repository unavailable" : "orchflows-public · codex/portability-repair",
    lastActivity: unreadable ? "Activity unavailable" : "4 minutes ago",
    unreadable,
    tickets,
  };
}

function completedRun(): NowRun {
  return {
    id: "20260818-ui-platform",
    objective: "Ship the secure read-only browser foundation",
    repository: "orchflows-public · main",
    lastActivity: "Yesterday, 8:42 PM",
    tickets: [
      ticket("00-platform", "complete", "complete", [], "Build the platform"),
      ticket("01-critique", "complete", "complete", ["00-platform"], "Critique the platform"),
      ticket("02-verify", "complete", "complete", ["01-critique"], "Verify the platform"),
    ],
  };
}

export function nowFixture(state: string): { runs: NowRun[]; paused: boolean; diagnostic: string } {
  if (state === "no-active-runs") return { runs: [completedRun()], paused: false, diagnostic: "" };
  if (state === "unreadable-data") return {
    runs: [attentionRun(true), completedRun()], paused: false,
    diagnostic: "One run contains malformed or unreadable canonical state. It remains visible and is never guessed.",
  };
  if (state === "needs-attention") return { runs: [attentionRun(), completedRun()], paused: false, diagnostic: "" };
  if (state === "live-paused") return { runs: [activeRun(), completedRun()], paused: true, diagnostic: "" };
  return { runs: [attentionRun(), activeRun(), completedRun()], paused: false, diagnostic: "" };
}
