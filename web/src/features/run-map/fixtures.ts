import type { RunDetail, TicketSummary } from "../../api/schema";

function projected(ticket: TicketSummary, patch: Partial<TicketSummary>): TicketSummary {
  return { ...ticket, ...patch, readiness: patch.readiness ?? ticket.readiness };
}

function activeTopology(run: RunDetail): RunDetail {
  if (run.tickets.length < 5) return run;
  const [spec, verify, foundation, render, gate, ...rest] = run.tickets;
  const tickets = [
    projected(spec, {
      status: "complete",
      depends_on: [],
      readiness: { state: "complete", dependencies: [], explanation: `${spec.id} is complete` }
    }),
    projected(verify, {
      status: "blocked",
      depends_on: [spec.id],
      readiness: { state: "attention", dependencies: [], explanation: `${verify.id} ended with status blocked` }
    }),
    projected(foundation, {
      status: "complete",
      depends_on: [spec.id],
      readiness: { state: "complete", dependencies: [], explanation: `${foundation.id} is complete` }
    }),
    projected(render, {
      status: "claimed",
      depends_on: [foundation.id],
      readiness: { state: "running", dependencies: [], explanation: `${render.id} is claimed` }
    }),
    projected(gate, {
      status: "pending",
      depends_on: [verify.id, render.id],
      readiness: {
        state: "waiting",
        dependencies: [verify.id, render.id],
        explanation: `${gate.id} waits for: ${verify.id}, ${render.id}`
      }
    }),
    ...rest.map((ticket) => projected(ticket, {
      depends_on: [gate.id],
      readiness: ticket.status === "suspended"
        ? { state: "attention", dependencies: [], explanation: `${ticket.id} is suspended` }
        : { state: "waiting", dependencies: [gate.id], explanation: `${ticket.id} waits for: ${gate.id}` }
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
      readiness: { state: "complete", dependencies: [], explanation: `${ticket.id} is complete` }
    }))
  };
}
