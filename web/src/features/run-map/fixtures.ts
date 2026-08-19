import type { RunDetail, TicketSummary } from "../../api/schema";
import type { CanonicalCause, CanonicalCausalReadiness } from "./model";

function projected(ticket: TicketSummary, patch: Partial<TicketSummary>): TicketSummary {
  return { ...ticket, ...patch, readiness: patch.readiness ?? ticket.readiness };
}

function readiness(
  state: TicketSummary["readiness"]["state"],
  dependencies: string[],
  explanation: string,
  cause: CanonicalCause = "none",
  causal_chain: string[] = []
): TicketSummary["readiness"] & CanonicalCausalReadiness {
  return { state, dependencies, explanation, cause, causal_chain };
}

function activeTopology(run: RunDetail): RunDetail {
  if (run.tickets.length < 5) return run;
  const [spec, verify, foundation, render, gate, ...rest] = run.tickets;
  const tickets = [
    projected(spec, {
      status: "complete",
      depends_on: [],
      readiness: readiness("complete", [], `${spec.id} is complete`, "none", [spec.id])
    }),
    projected(verify, {
      status: "blocked",
      depends_on: [spec.id],
      readiness: readiness("attention", [], `${verify.id} ended with status blocked`, "blocked_upstream", [verify.id])
    }),
    projected(foundation, {
      status: "complete",
      depends_on: [spec.id],
      readiness: readiness("complete", [], `${foundation.id} is complete`, "none", [foundation.id])
    }),
    projected(render, {
      status: "claimed",
      depends_on: [foundation.id],
      readiness: readiness("running", [], `${render.id} is claimed`, "none", [render.id])
    }),
    projected(gate, {
      status: "pending",
      depends_on: [verify.id, render.id],
      readiness: readiness(
        "waiting",
        [verify.id, render.id],
        `${gate.id} waits for blocked upstream ${verify.id}`,
        "blocked_upstream",
        [gate.id, verify.id]
      )
    }),
    ...rest.map((ticket) => projected(ticket, {
      depends_on: [gate.id],
      readiness: ticket.status === "suspended"
        ? readiness("attention", [], `${ticket.id} is suspended`, "suspended_handoff", [ticket.id])
        : readiness("waiting", [gate.id], `${ticket.id} waits for: ${gate.id}`, "blocked_upstream", [ticket.id, gate.id, verify.id])
    }))
  ];
  return { ...run, active: true, tickets };
}

export function runForIdentity(run: RunDetail, identity: string): RunDetail {
  if (identity === "malformed-topology") return run;
  const projectedRun = activeTopology(run);
  if (identity !== "completed") return projectedRun;
  return {
    ...projectedRun,
    active: false,
    tickets: projectedRun.tickets.map((ticket) => projected(ticket, {
      status: "complete",
      readiness: readiness("complete", [], `${ticket.id} is complete`, "none", [ticket.id])
    }))
  };
}
