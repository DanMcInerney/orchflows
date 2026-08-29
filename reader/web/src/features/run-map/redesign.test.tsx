import { cleanup, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { runForIdentity } from "./fixtures";
import { skillSequence, type ReadinessState, type RunMapModel, type TicketSummary } from "./model";
import { RunMapView } from "./RunMapView";

interface MockNode { id: string; type?: string; data: Record<string, unknown> }
interface MockEdge { id: string; ariaLabel?: string }

vi.mock("@xyflow/react", () => ({
  ReactFlowProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  ReactFlow: ({ children, nodes, edges, onNodeClick, ...props }: {
    children: ReactNode;
    nodes: MockNode[];
    edges: MockEdge[];
    onNodeClick: (event: unknown, node: MockNode) => void;
    "aria-label": string;
  }) => <div aria-label={props["aria-label"]}>
    {nodes.map((node) => {
      const ticket = node.data.ticket as TicketSummary | undefined;
      const group = node.data.group as { label: string } | undefined;
      return <button key={node.id} type="button" onClick={(event) => onNodeClick(event, node)}>
        {ticket?.id ?? group?.label ?? node.id}
      </button>;
    })}
    <ul aria-label="Projected dependency edges">{edges.map((edge) => <li key={edge.id}>{edge.ariaLabel ?? edge.id}</li>)}</ul>
    {children}
  </div>,
  Background: () => null,
  MiniMap: ({ ariaLabel }: { ariaLabel: string }) => <div aria-label={ariaLabel} />,
  Controls: ({ "aria-label": label }: { "aria-label": string }) => <div aria-label={label} />,
  Handle: () => null,
  Position: { Left: "left", Right: "right" }
}));

afterEach(cleanup);

interface TicketPatch {
  executor?: string;
  claimed_by?: string;
  claimed_at?: string;
  depends_on?: string[];
}

function ticket(id: string, status: string, state: ReadinessState, patch: TicketPatch = {}): TicketSummary {
  return {
    id,
    status,
    executor: patch.executor ?? "orch-tdd",
    bound: "90m",
    claimed_at: patch.claimed_at ?? "",
    claimed_by: patch.claimed_by ?? "",
    depends_on: patch.depends_on ?? [],
    unreadable: false,
    readiness: { state, dependencies: [], explanation: `${id} canonical ${state}`, cause: "none", causal_chain: [id] }
  };
}

/**
 * Four tickets keep `runForIdentity` from re-projecting the topology (`activeTopology`
 * only rewrites runs of five or more), so what this spec asserts is what it supplied.
 */
function drilldownTickets(): TicketSummary[] {
  return [
    ticket("T/gate", "pending", "waiting", { executor: "orch-verify", depends_on: ["T-render"] }),
    ticket("T-render", "claimed", "running", {
      executor: "orch-render",
      claimed_by: "agent-b",
      claimed_at: "2026-01-01T03:00:00Z",
      depends_on: ["T-plan"]
    }),
    ticket("T-spec", "complete", "complete", {
      executor: "orch-spec",
      claimed_by: "agent-a",
      claimed_at: "2026-01-01T01:00:00Z"
    }),
    ticket("T-plan", "complete", "complete", {
      executor: "orch-decompose",
      claimed_by: "agent-a",
      claimed_at: "2026-01-01T02:00:00Z",
      depends_on: ["T-spec"]
    })
  ];
}

/** Seven tickets: enough for `activeTopology` to apply the identity projection. */
function sevenTickets(): TicketSummary[] {
  return ["G1", "G2", "G3", "G4", "G5", "G6", "G7"].map((id, index) =>
    ticket(id, index === 6 ? "suspended" : "pending", "ready", { claimed_by: "corpus-agent" })
  );
}

function projection(tickets: TicketSummary[]): RunMapModel {
  return {
    runs: [{ id: "run-gamma", ticket_count: tickets.length, active: true, tickets }],
    run: { id: "run-gamma", active: true, tickets, diagnostics: [], counts: {} }
  };
}

const ready = (value: RunMapModel) => ({ status: "ready", model: value, error: null } as const);

function renderedSteps(container: HTMLElement) {
  return [...container.querySelectorAll<HTMLAnchorElement>(".run-skills__node")].map((node) => ({
    ticket: node.querySelector(".run-skills__ticket")?.textContent ?? "",
    skill: node.querySelector("b")?.textContent ?? "",
    phase: node.getAttribute("data-phase"),
    continuity: node.getAttribute("data-continuity"),
    agent: node.getAttribute("data-agent"),
    href: node.getAttribute("href")
  }));
}

describe("run detail drill-down", () => {
  it("sequences skills by when they ran and pushes every unstarted skill behind them", () => {
    const tickets = drilldownTickets();
    tickets.push(ticket("T-close", "pending", "waiting", {
      executor: "orch-integrate",
      claimed_by: "agent-c",
      depends_on: ["T/gate"]
    }));

    const sequence = skillSequence(tickets);

    expect(sequence.steps.map((step) => step.ticket.id)).toEqual([
      "T-spec", "T-plan", "T-render", "T/gate", "T-close"
    ]);
    expect(sequence.steps.map((step) => step.phase)).toEqual([
      "ran", "ran", "running", "remaining", "remaining"
    ]);
    expect(sequence.steps.map((step) => step.order)).toEqual([1, 2, 3, 4, 5]);
    expect({ ran: sequence.ran, running: sequence.running, remaining: sequence.remaining })
      .toEqual({ ran: 2, running: 1, remaining: 2 });
  });

  it("claims same-subagent only for equal non-empty claims and never across an empty one", () => {
    const tickets = drilldownTickets();
    tickets.push(ticket("T-close", "pending", "waiting", {
      executor: "orch-integrate",
      claimed_by: "agent-c",
      depends_on: ["T/gate"]
    }));

    const sequence = skillSequence(tickets);

    expect(sequence.steps.map((step) => [step.ticket.id, step.agent, step.continuity])).toEqual([
      ["T-spec", "agent-a", "first"],
      ["T-plan", "agent-a", "same-subagent"],
      ["T-render", "agent-b", "new-subagent"],
      ["T/gate", "", "unclaimed"],
      ["T-close", "agent-c", "unclaimed"]
    ]);
  });

  it("treats a whitespace-only claim as unclaimed rather than as a subagent identity", () => {
    const sequence = skillSequence([
      ticket("W1", "claimed", "running", { claimed_by: "  ", claimed_at: "2026-01-01T01:00:00Z" }),
      ticket("W2", "claimed", "running", { claimed_by: "  ", claimed_at: "2026-01-01T02:00:00Z", depends_on: ["W1"] })
    ]);

    expect(sequence.steps.map((step) => step.agent)).toEqual(["", ""]);
    expect(sequence.steps.map((step) => step.continuity)).toEqual(["first", "unclaimed"]);
  });

  it("renders the sequence, its phases and its subagent seams on the run detail view", () => {
    const { container } = render(
      <RunMapView state={ready(projection(drilldownTickets()))} route={{ run: "run-gamma", fixture: "full-expanded" }} />
    );

    expect(screen.getByRole("heading", { name: "2 of 4 skills run" })).not.toBeNull();
    expect(renderedSteps(container)).toEqual([
      { ticket: "T-spec", skill: "orch-spec", phase: "ran", continuity: "first", agent: "agent-a", href: "/runs/run-gamma/tickets/T-spec?fixture=full-expanded" },
      { ticket: "T-plan", skill: "orch-decompose", phase: "ran", continuity: "same-subagent", agent: "agent-a", href: "/runs/run-gamma/tickets/T-plan?fixture=full-expanded" },
      { ticket: "T-render", skill: "orch-render", phase: "running", continuity: "new-subagent", agent: "agent-b", href: "/runs/run-gamma/tickets/T-render?fixture=full-expanded" },
      { ticket: "T/gate", skill: "orch-verify", phase: "remaining", continuity: "unclaimed", agent: "", href: "/runs/run-gamma/tickets/T%2Fgate?fixture=full-expanded" }
    ]);
    expect([...container.querySelectorAll(".run-skills__seam")].map((seam) => seam.getAttribute("data-continuity")))
      .toEqual(["same-subagent", "new-subagent", "unclaimed"]);
  });

  it("names every skill node so the phase and the subagent boundary survive without sight", () => {
    render(
      <RunMapView state={ready(projection(drilldownTickets()))} route={{ run: "run-gamma", fixture: "full-expanded" }} />
    );

    expect(screen.getByRole("link", { name: "orch-spec, ticket T-spec, already run, first skill in this run" })).not.toBeNull();
    expect(screen.getByRole("link", { name: "orch-decompose, ticket T-plan, already run, same subagent as the previous skill" })).not.toBeNull();
    expect(screen.getByRole("link", { name: "orch-render, ticket T-render, running now, new subagent" })).not.toBeNull();
    expect(screen.getByRole("link", { name: "orch-verify, ticket T/gate, still to run, unclaimed, so no subagent continuity is claimed" })).not.toBeNull();
  });

  it("keeps the sequence on the drill-down path at the grouped summary, not only in the graph", () => {
    const { container } = render(
      <RunMapView state={ready(projection(drilldownTickets()))} route={{ run: "run-gamma", fixture: "summary-active" }} />
    );

    expect(screen.getByRole("heading", { name: "Readiness, without invented phases" })).not.toBeNull();
    expect(renderedSteps(container).map((step) => step.ticket)).toEqual(["T-spec", "T-plan", "T-render", "T/gate"]);
  });

  it("marks nothing still to run once the run is terminal", () => {
    const { container } = render(
      <RunMapView state={ready(projection(drilldownTickets()))} route={{ run: "run-delta", fixture: "completed" }} />
    );

    expect(screen.getByRole("heading", { name: "4 of 4 skills run" })).not.toBeNull();
    expect(renderedSteps(container).map((step) => step.phase)).toEqual(["ran", "ran", "ran", "ran"]);
    expect(container.querySelector(".run-skills__node[data-phase='remaining']")).toBeNull();
  });

  it("still sequences skills when the canonical topology is cyclic", () => {
    const cyclic = [
      ticket("E1", "ready", "ready", { executor: "orch-tdd", depends_on: ["E3"] }),
      ticket("E2", "pending", "waiting", { executor: "orch-verify", depends_on: ["E1"] }),
      ticket("E3", "pending", "waiting", { executor: "orch-repair", depends_on: ["E2"] })
    ];

    const sequence = skillSequence(cyclic);

    expect(sequence.steps).toHaveLength(3);
    expect(sequence.remaining).toBe(3);
    expect(new Set(sequence.steps.map((step) => step.ticket.id))).toEqual(new Set(["E1", "E2", "E3"]));
  });

  it("reads whether a skill ran off readiness, so a stale claim never counts as run", () => {
    const sequence = skillSequence([
      ticket("S1", "claimed", "waiting", { claimed_by: "agent-a", claimed_at: "2026-01-01T01:00:00Z" }),
      ticket("S2", "blocked", "attention", { claimed_by: "agent-a", claimed_at: "2026-01-01T02:00:00Z" }),
      ticket("S3", "blocked", "attention", { depends_on: ["S2"] })
    ]);

    expect(sequence.steps.map((step) => [step.ticket.id, step.phase])).toEqual([
      ["S2", "ran"], ["S1", "remaining"], ["S3", "remaining"]
    ]);
  });

  it("gives every covered run-map identity all three subagent readings to render", () => {
    for (const identity of ["summary-active", "full-collapsed", "full-expanded", "blocked-causal", "completed"]) {
      const sequence = skillSequence(runForIdentity(projection(sevenTickets()).run, identity, "run-gamma").tickets);
      const continuity = new Set(sequence.steps.map((step) => step.continuity));

      expect([identity, [...continuity].sort()]).toEqual([
        identity, ["first", "new-subagent", "same-subagent", "unclaimed"]
      ]);
    }
  });

  it("names a skill even when the executor field is unavailable", () => {
    const sequence = skillSequence([ticket("X1", "pending", "waiting", { executor: "" })]);

    expect(sequence.steps[0].skill).toBe("unnamed skill");
  });
});
