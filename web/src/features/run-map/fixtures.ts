import type { CanonicalCause, CanonicalCausalReadiness, RunDetail, TicketSummary } from "./model";

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

function fixtureTicket(id: string): TicketSummary {
  return {
    id,
    status: "pending",
    executor: "orch-render",
    bound: "90m",
    claimed_at: "",
    claimed_by: "",
    depends_on: [],
    unreadable: false,
    readiness: readiness("ready", [], `${id} has complete dependencies and is eligible`, "none", [id])
  };
}

function deterministicRun(runId: string, identity: string): RunDetail {
  if (identity === "malformed-topology") {
    const [one, two, three, four] = ["E1", "E2", "E3", "E4"].map(fixtureTicket);
    return {
      id: runId || "run-epsilon",
      active: true,
      counts: { pending: 3, ready: 1 },
      tickets: [
        projected(one, { status: "ready", depends_on: [three.id], readiness: readiness("waiting", [three.id], `${one.id} waits for: ${three.id}`, "malformed_topology", [one.id, three.id]) }),
        projected(two, { depends_on: [one.id], readiness: readiness("waiting", [one.id], `${two.id} waits for: ${one.id}`, "malformed_topology", [two.id, one.id]) }),
        projected(three, { depends_on: [two.id], readiness: readiness("waiting", [two.id], `${three.id} waits for: ${two.id}`, "malformed_topology", [three.id, two.id]) }),
        projected(four, { depends_on: ["ZZ9", one.id], readiness: readiness("attention", ["ZZ9"], `${four.id} names missing dependencies: ZZ9`, "malformed_topology", [four.id, "ZZ9"]) })
      ],
      diagnostics: [
        { kind: "cycle", ticket_ids: [one.id, three.id, two.id], message: `Dependency cycle: ${one.id} → ${three.id} → ${two.id} → ${one.id}` },
        { kind: "dangling", ticket_ids: [four.id, "ZZ9"], message: `${four.id} depends on missing ticket ZZ9.` }
      ]
    };
  }
  return {
    id: runId || (identity === "completed" ? "run-delta" : "run-gamma"),
    active: identity !== "completed",
    counts: { complete: 2, blocked: 1, claimed: 1, pending: 2 },
    diagnostics: [],
    tickets: ["G1", "G2", "G3", "G4", "G5", "G6", "G7"].map(fixtureTicket)
  };
}

/**
 * Claim stamps the covered identities need. `claimed_by` is a claim-time field, so an
 * unstarted ticket carries none: the first two steps share one subagent, the next two a
 * second, the suspended tail a third, and everything still waiting stays unclaimed. That
 * gives every covered identity all three subagent-continuity readings at once.
 */
const SPEC_AGENT = "agent-spec-01";
const BUILD_AGENT = "agent-build-02";
const HANDOFF_AGENT = "agent-gate-03";

function activeTopology(run: RunDetail): RunDetail {
  if (run.tickets.length < 5) return run;
  const [spec, verify, foundation, render, gate, ...rest] = run.tickets;
  const tickets = [
    projected(spec, {
      status: "complete",
      depends_on: [],
      claimed_by: SPEC_AGENT,
      claimed_at: "2026-01-01T09:00:00Z",
      readiness: readiness("complete", [], `${spec.id} is complete`, "none", [spec.id])
    }),
    projected(verify, {
      status: "blocked",
      depends_on: [spec.id],
      claimed_by: SPEC_AGENT,
      claimed_at: "2026-01-01T09:40:00Z",
      readiness: readiness("attention", [], `${verify.id} ended with status blocked`, "blocked_upstream", [verify.id])
    }),
    projected(foundation, {
      status: "complete",
      depends_on: [spec.id],
      claimed_by: BUILD_AGENT,
      claimed_at: "2026-01-01T10:10:00Z",
      readiness: readiness("complete", [], `${foundation.id} is complete`, "none", [foundation.id])
    }),
    projected(render, {
      status: "claimed",
      depends_on: [foundation.id],
      claimed_by: BUILD_AGENT,
      claimed_at: "2026-01-01T11:05:00Z",
      readiness: readiness("running", [], `${render.id} is claimed`, "none", [render.id])
    }),
    projected(gate, {
      status: "pending",
      depends_on: [verify.id, render.id],
      claimed_by: "",
      claimed_at: "",
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
      claimed_by: ticket.status === "suspended" ? HANDOFF_AGENT : "",
      claimed_at: ticket.status === "suspended" ? "2026-01-01T12:20:00Z" : "",
      readiness: ticket.status === "suspended"
        ? readiness("attention", [], `${ticket.id} is suspended`, "suspended_handoff", [ticket.id])
        : readiness("waiting", [gate.id], `${ticket.id} waits for: ${gate.id}`, "blocked_upstream", [ticket.id, gate.id, verify.id])
    }))
  ];
  return { ...run, active: true, tickets };
}

export function runForIdentity(run: RunDetail | null, identity: string, requestedRun = ""): RunDetail {
  run = run ?? deterministicRun(requestedRun, identity);
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

export const fixtures = { runForIdentity };
