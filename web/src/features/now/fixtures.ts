import type { NowRun, NowTicket, ReadinessState } from "./model";

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
    repository: "orchflows-public",
    client: "Codex desktop",
    lastActivity: "18 seconds ago",
    terminalAt: "",
    terminalStatus: "",
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

function neighbourRun(): NowRun {
  return {
    id: "20260824-atlas-onboarding",
    objective: "Cut the first-run onboarding path down to one readable page",
    repository: "atlas-web",
    lastActivity: "6 minutes ago",
    terminalAt: "",
    terminalStatus: "",
    tickets: [
      ticket("00-scope", "complete", "complete", [], "Fix the onboarding boundary"),
      ticket("01-copy", "claimed", "running", ["00-scope"], "Rewrite the welcome copy"),
      ticket("02-verify", "pending", "waiting", ["01-copy"], "Verify the shortened path"),
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
    repository: unreadable ? "" : "orchflows-public",
    lastActivity: unreadable ? "Activity unavailable" : "4 minutes ago",
    terminalAt: "",
    terminalStatus: "",
    unreadable,
    tickets,
  };
}

function completedRun(): NowRun {
  return {
    id: "20260818-ui-platform",
    objective: "Ship the secure read-only browser foundation",
    repository: "orchflows-public",
    lastActivity: "Yesterday, 8:42 PM",
    terminalAt: "2026-08-25T09:15:04Z",
    terminalStatus: "complete",
    tickets: [
      ticket("00-platform", "complete", "complete", [], "Build the platform"),
      ticket("01-critique", "complete", "complete", ["00-platform"], "Critique the platform"),
      ticket("02-verify", "complete", "complete", ["01-critique"], "Verify the platform"),
    ],
  };
}

function earlierRun(): NowRun {
  return {
    id: "20260817-ledger-migration",
    objective: "Migrate the ledger reader onto the shared transport",
    repository: "ledger-service",
    lastActivity: "Sunday, 4:11 PM",
    terminalAt: "2026-08-24T20:42:11Z",
    terminalStatus: "limited",
    tickets: [
      ticket("00-plan", "complete", "complete", [], "Plan the migration"),
      ticket("01-move", "complete", "complete", ["00-plan"], "Move the reader"),
    ],
  };
}

export function nowFixture(state: string): { runs: NowRun[]; paused: boolean; diagnostic: string } {
  if (state === "empty") return { runs: [], paused: false, diagnostic: "" };
  if (state === "no-active-runs") return { runs: [completedRun(), earlierRun()], paused: false, diagnostic: "" };
  if (state === "unreadable-data") return {
    runs: [attentionRun(true), completedRun()], paused: false,
    diagnostic: "One run contains malformed or unreadable canonical state. It remains visible and is never guessed.",
  };
  if (state === "needs-attention") return { runs: [attentionRun(), completedRun()], paused: false, diagnostic: "" };
  if (state === "live-paused") return { runs: [activeRun(), completedRun()], paused: true, diagnostic: "" };
  return { runs: [attentionRun(), activeRun(), neighbourRun(), completedRun(), earlierRun()], paused: false, diagnostic: "" };
}

export const fixtures = { get: nowFixture };
