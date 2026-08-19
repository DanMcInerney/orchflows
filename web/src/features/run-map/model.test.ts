import { describe, expect, it } from "vitest";
import type { ReadinessState, TicketSummary } from "../../api/schema";
import {
  authoritativeCausalFocus,
  buildTopology,
  filterTickets,
  readinessGroups,
  type CanonicalCause
} from "./model";

function ticket(
  id: string,
  status: string,
  state: ReadinessState,
  depends_on: string[] = [],
  dependencies: string[] = depends_on,
  cause: CanonicalCause = "none",
  causal_chain: string[] = [id]
): TicketSummary {
  return {
    id,
    status,
    executor: "orch-render",
    bound: "90m",
    claimed_at: "",
    claimed_by: "",
    depends_on,
    unreadable: false,
    readiness: { state, dependencies, explanation: `${id} canonical ${state}`, cause, causal_chain } as TicketSummary["readiness"] & { cause: CanonicalCause; causal_chain: string[] }
  };
}

describe("run-map topology model", () => {
  it("preserves every canonical edge and makes malformed topology explicit", () => {
    const tickets = [
      ticket("A", "ready", "ready", ["C"]),
      ticket("B", "pending", "waiting", ["A", "MISSING"]),
      ticket("C", "pending", "waiting", ["B"]),
      { ...ticket("B", "pending", "unknown"), unreadable: true }
    ];
    const model = buildTopology(tickets);
    expect(model.edges.map(({ source, target, missingSource }) => ({ source, target, missingSource }))).toEqual([
      { source: "C", target: "A", missingSource: false },
      { source: "A", target: "B", missingSource: false },
      { source: "MISSING", target: "B", missingSource: true },
      { source: "B", target: "C", missingSource: false }
    ]);
    expect(model.diagnostics.map((diagnostic) => diagnostic.kind)).toEqual([
      "duplicate", "dangling", "unreadable", "cycle"
    ]);
    expect(model.diagnostics.at(-1)?.message).toContain("A → C → B → A");
  });

  it("keeps summary groups reversible to canonical readiness and status", () => {
    const groups = readinessGroups([
      ticket("A", "claimed", "running"),
      ticket("B", "pending", "waiting"),
      ticket("C", "blocked", "attention")
    ]);
    expect(groups.map((group) => [group.label, group.ticketIds, group.statuses])).toEqual([
      ["Needs attention", ["C"], ["blocked"]],
      ["Running", ["A"], ["claimed"]],
      ["Waiting", ["B"], ["pending"]]
    ]);
  });

  it("filters by exact readiness while preserving search by id or executor", () => {
    const tickets = [
      ticket("A-build", "claimed", "running"),
      { ...ticket("B-check", "pending", "unknown"), executor: "orch-verify" },
      ticket("C-ready", "ready", "ready")
    ];
    expect(filterTickets(tickets, "active", "", []).map(({ id }) => id)).toEqual(["A-build"]);
    expect(filterTickets(tickets, "problems", "verify", []).map(({ id }) => id)).toEqual(["B-check"]);
    expect(filterTickets(tickets, "ready", "C-ready", []).map(({ id }) => id)).toEqual(["C-ready"]);
  });

  it("follows only authoritative readiness dependencies for the shortest causal chain", () => {
    const root = ticket("ROOT", "suspended", "attention", [], []);
    const middle = ticket("MID", "pending", "waiting", ["ROOT"], ["ROOT"]);
    const leaf = ticket("LEAF", "pending", "waiting", ["IGNORED", "MID"], ["MID"], "suspended_handoff", ["LEAF", "MID", "ROOT"]);
    leaf.readiness.explanation = "LEAF waits for suspended ROOT";
    const focus = authoritativeCausalFocus("LEAF", [leaf, middle, root]);
    expect(focus.ticketIds).toEqual(["LEAF", "MID", "ROOT"]);
    expect(focus.edgeIds).toEqual(["MID->LEAF", "ROOT->MID"]);
    expect(focus.kind).toBe("suspended");
    expect(focus.summary).toBe("Waiting on suspended handoff ROOT.");
    expect(focus.evidence).toBe("LEAF waits for suspended ROOT");
  });

  it("does not infer a wait from graph edges when canonical readiness names none", () => {
    const ready = ticket("READY", "ready", "ready", ["UPSTREAM"], [], "none", ["READY"]);
    const focus = authoritativeCausalFocus("READY", [ready, ticket("UPSTREAM", "claimed", "running")]);
    expect(focus.kind).toBe("none");
    expect(focus.ticketIds).toEqual(["READY"]);
  });
});
