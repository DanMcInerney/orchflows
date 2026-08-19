import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ExperienceSnapshot, ReadinessState, TicketSummary } from "../../api/schema";
import type { LocationState } from "../../state/location";
import { RunMapView } from "./RunMapView";

interface MockNode {
  id: string;
  type?: string;
  data: Record<string, unknown>;
}

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
      return <button key={node.id} type="button" data-causal={String(node.data.causal ?? "off")} onClick={(event) => onNodeClick(event, node)}>
        {ticket?.id ?? group?.label ?? node.id}
      </button>;
    })}
    <ul aria-label="Projected dependency edges">{edges.map((edge) => <li key={edge.id}>{edge.ariaLabel ?? edge.id}</li>)}</ul>
    {children}
  </div>,
  Background: () => null,
  MiniMap: ({ ariaLabel }: { ariaLabel: string }) => <div aria-label={ariaLabel} />,
  Controls: ({ "aria-label": label }: { "aria-label": string }) => <div aria-label={label}><button type="button">Zoom in</button><button type="button">Zoom out</button><button type="button">Fit view</button></div>
}));

afterEach(cleanup);

function ticket(id: string, status: string, state: ReadinessState): TicketSummary {
  return {
    id,
    status,
    executor: "orch-render",
    bound: "90m",
    claimed_at: "2026-01-01T00:00:00Z",
    claimed_by: "fixture-agent",
    depends_on: [],
    unreadable: false,
    readiness: { state, dependencies: [], explanation: `${id} canonical ${state}`, cause: "none", causal_chain: [id] }
  };
}

function snapshot(prefix = "G"): ExperienceSnapshot {
  const tickets = [
    ticket(`${prefix}1`, "complete", "complete"),
    ticket(`${prefix}2`, "blocked", "attention"),
    ticket(`${prefix}3`, "complete", "complete"),
    ticket(`${prefix}4`, "claimed", "running"),
    ticket(`${prefix}5`, "pending", "waiting"),
    ticket(`${prefix}6`, "suspended", "attention")
  ];
  return {
    schema: "orchflows.experience.v1",
    navigation: [],
    selection: { view: "run-map", run: "run-gamma", ticket: "", session: "" },
    runs: [
      { id: "run-gamma", ticket_count: tickets.length, active: true, objective: "", repository: "", client: "", last_activity: "", unreadable: false, tickets },
      { id: "run-delta", ticket_count: 3, active: false, objective: "", repository: "", client: "", last_activity: "", unreadable: false, tickets: [] }
    ],
    run: { id: "run-gamma", active: true, tickets, diagnostics: [], counts: { claimed: 1, pending: 1 } },
    ticket: null,
    sessions: { items: [], diagnostics: [], empty: true },
    session: null,
    friction: { items: [], skipped: 0, unreadable: 0 }
  };
}

function location(fixture: string): LocationState {
  return { view: "run-map", run: "run-gamma", ticket: "", session: "", fixture };
}

describe("RunMapView", () => {
  it("expands semantically while preserving filters and exposing keyboard graph controls", () => {
    const view = render(<RunMapView snapshot={snapshot()} location={location("summary-active")} />);
    expect(view.container.querySelector(".foundation-view[data-view='run-map']")).not.toBeNull();
    expect(screen.getByRole("heading", { name: "Readiness, without invented phases" })).not.toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Open canonical graph/i }));
    expect(screen.getByRole("heading", { name: "Readiness groups collapsed" })).not.toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Active" }));
    fireEvent.click(screen.getByRole("button", { name: /Expand all tickets/i }));
    expect(screen.getByRole("heading", { name: "Every canonical dependency" })).not.toBeNull();
    expect(screen.getByRole("button", { name: "G4" })).not.toBeNull();
    expect(screen.queryByRole("button", { name: "G1" })).toBeNull();
    expect(screen.getByLabelText("Run graph minimap")).not.toBeNull();
    expect(screen.getByRole("button", { name: "Fit view" })).not.toBeNull();
    expect(screen.getByRole("button", { name: "Active" }).getAttribute("aria-pressed")).toBe("true");
  });

  it("focuses the shortest authoritative blocking chain and dims irrelevant topology", async () => {
    render(<RunMapView snapshot={snapshot()} location={location("blocked-causal")} />);
    await screen.findByRole("heading", { name: "G5" });
    expect(screen.getByText("Waiting on failed or blocked upstream work G2.")).not.toBeNull();
    expect(screen.getByText("G5 ← G2")).not.toBeNull();
    expect(screen.getByRole("button", { name: "G4" }).getAttribute("data-causal")).toBe("dimmed");
    expect(screen.getByRole("button", { name: "G2" }).getAttribute("data-causal")).toBe("focus");
    expect(screen.getByRole("button", { name: "Why waiting?" }).getAttribute("aria-pressed")).toBe("true");
  });

  it("keeps malformed topology explicit without offering mutation controls", () => {
    const malformed = snapshot();
    if (!malformed.run) throw new Error("fixture run missing");
    malformed.run.tickets = [
      { ...ticket("E1", "ready", "ready"), depends_on: ["E3"] },
      { ...ticket("E2", "pending", "waiting"), depends_on: ["E1"] },
      { ...ticket("E3", "pending", "waiting"), depends_on: ["E2", "ZZ9"] }
    ];
    malformed.run.diagnostics = [
      { kind: "dangling", ticket_ids: ["E3", "ZZ9"], message: "E3 depends on missing ticket ZZ9." },
      { kind: "cycle", ticket_ids: ["E1", "E2", "E3"], message: "Dependency cycle: E1 → E3 → E2 → E1" }
    ];
    render(<RunMapView snapshot={malformed} location={location("malformed-topology")} />);
    expect(screen.getByRole("heading", { name: "2 canonical graph issues" })).not.toBeNull();
    expect(screen.getByText("E3 depends on missing ticket ZZ9.")).not.toBeNull();
    expect(screen.getByText(/Dependency cycle:/)).not.toBeNull();
    expect(screen.queryByRole("button", { name: /start|edit|delete|retry/i })).toBeNull();
    expect(screen.getByText("Observe only")).not.toBeNull();
  });

  it("holds the projected run while paused and adopts the latest safe snapshot on resume", async () => {
    const first = snapshot("G");
    const second = snapshot("N");
    const view = render(<RunMapView snapshot={first} location={location("full-expanded")} />);
    expect(screen.getByRole("button", { name: "G4" })).not.toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Pause live" }));
    view.rerender(<RunMapView snapshot={second} location={location("full-expanded")} />);
    expect(screen.getByRole("button", { name: "G4" })).not.toBeNull();
    expect(screen.queryByRole("button", { name: "N4" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Resume live" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "N4" })).not.toBeNull());
    expect(screen.queryByRole("button", { name: "G4" })).toBeNull();
  });

  it("preserves disclosure context when opening and closing a persistent inspector", () => {
    render(<RunMapView snapshot={snapshot()} location={location("full-expanded")} />);
    fireEvent.change(screen.getByPlaceholderText("Search ticket or executor"), { target: { value: "G4" } });
    fireEvent.click(screen.getByRole("button", { name: "G4" }));
    expect(screen.getByRole("heading", { name: "G4" })).not.toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Close inspector" }));
    expect(screen.getByPlaceholderText("Search ticket or executor").getAttribute("value")).toBe("G4");
    expect(screen.getByRole("heading", { name: "Every canonical dependency" })).not.toBeNull();
  });
});
