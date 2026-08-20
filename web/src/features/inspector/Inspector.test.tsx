import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import type { ExperienceSnapshot } from "../../api/schema";
import type { LocationState } from "../../state/location";
import TicketInspector from "./Inspector";

function snapshot(overrides: Record<string, unknown> = {}): ExperienceSnapshot {
  const ticket = {
    id: "G1",
    status: "complete",
    executor: "orch-render",
    bound: "90m",
    claimed_at: "2026-01-01T00:00:00Z",
    claimed_by: "fixture-agent",
    depends_on: ["G0"],
    unreadable: false,
    readiness: { state: "complete", dependencies: [], explanation: "G1 is complete", cause: "none", causal_chain: [] },
    sections: { objective: "Prove the inspector without exposing private activity.", result: "The safe result." },
    verification: {
      state: "rows",
      rows: [
        { "#": "1", verdict: "PASS", oracle: "tools/validate.py", class: "deterministic", evidence: "exit 0" },
        { "#": "2", verdict: "FAIL", oracle: "install.py --dry-run", class: "deterministic", evidence: "3 scripts, 4 expected" }
      ]
    },
    inputs: ["accepted schema"],
    write_scope: ["web/src/features/inspector"],
    pack: "orch-design-pack",
    history: [],
    raw: "",
    ...overrides
  };
  return {
    schema: "orchflows.experience.v1",
    navigation: [],
    selection: { view: "ticket", run: "run-gamma", ticket: "G1", session: "" },
    runs: [], run: null, ticket, sessions: { items: [], diagnostics: [], empty: true }, session: null,
    friction: { items: [], skipped: 0, unreadable: 0 }
  } as unknown as ExperienceSnapshot;
}

function location(fixture: string, ticket = "G1"): LocationState {
  return { view: "ticket", run: "run-gamma", ticket, session: "", fixture };
}

afterEach(() => {
  cleanup();
  window.history.replaceState({}, "", "/");
});

describe("TicketInspector", () => {
  it("opens a direct-linked tab and keeps pointer selection in the URL", async () => {
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G1?fixture=running-overview&tab=proof");
    const { container } = render(<TicketInspector snapshot={snapshot()} location={location("running-overview")} />);

    expect(container.querySelector(".foundation-view.ticket-inspector")).not.toBeNull();
    expect(screen.getByRole("tab", { name: /Proof/ }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByRole("heading", { name: "Criteria and verdicts" })).not.toBeNull();

    await userEvent.click(screen.getByRole("tab", { name: "Details" }));
    expect(screen.getByRole("heading", { name: "Routing and limits" })).not.toBeNull();
    expect(new URLSearchParams(window.location.search).get("tab")).toBe("details");
  });

  it("gives keyboard tab selection the same behavior as pointer selection", async () => {
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G1?fixture=running-overview");
    render(<TicketInspector snapshot={snapshot()} location={location("running-overview")} />);
    const overview = screen.getByRole("tab", { name: "Overview" });
    overview.focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Details" }).getAttribute("aria-selected")).toBe("true");
    expect(new URLSearchParams(window.location.search).get("tab")).toBe("details");
  });

  it("renders passing and failing proof identities without losing oracle evidence", () => {
    const passing = snapshot();
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G1?fixture=proof-pass");
    const { unmount } = render(<TicketInspector snapshot={passing} location={location("proof-pass")} />);
    expect(screen.getAllByText("PASS")).toHaveLength(3);
    expect(screen.queryByText("FAIL")).toBeNull();
    expect(screen.getByText("install.py --dry-run")).not.toBeNull();
    expect(screen.getByText("plan named 4 scripts, 4 expected")).not.toBeNull();
    unmount();

    const failing = snapshot();
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G1?fixture=proof-fail");
    render(<TicketInspector snapshot={failing} location={location("proof-fail")} />);
    expect(screen.getByText("FAIL")).not.toBeNull();
    expect(screen.getByLabelText("Ticket state: failed")).not.toBeNull();
    expect(screen.getByText("Criterion 3 failed")).not.toBeNull();
    expect(screen.getByText(/install.py --dry-run: plan named 3 scripts/)).not.toBeNull();
    expect(screen.getAllByText("deterministic", { selector: "span" })).toHaveLength(3);
  });

  it("shows only friction linked by both run and ticket", () => {
    const value = snapshot();
    value.friction.items = ([
      { ts: "2026-08-01T00:00:00Z", run: "run-gamma", ticket: "G1", category: "contract-gap", observed: "Linked observation", expected: "Linked expectation", host: "fixture" },
      { ts: "2026-08-02T00:00:00Z", run: "run-gamma", ticket: "G2", category: "workaround", observed: "Other ticket", expected: "Not shown", host: "fixture" }
    ] as unknown) as ExperienceSnapshot["friction"]["items"];
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G1?fixture=friction-present");
    render(<TicketInspector snapshot={value} location={location("friction-present")} />);
    expect(screen.getByText("Linked observation")).not.toBeNull();
    expect(screen.queryByText("contract-gap")).toBeNull();
    expect(screen.queryByText("Other ticket")).toBeNull();
  });

  it("states that history is unavailable instead of inferring transcript activity", () => {
    const value = snapshot({ history: [{ ts: "2026-08-01", event: "tool_pre", agent: "worker", detail: "private activity" }] });
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G7?fixture=history-unavailable");
    render(<TicketInspector snapshot={value} location={location("history-unavailable", "G7")} />);
    expect(screen.getByRole("heading", { name: "History unavailable" })).not.toBeNull();
    expect(screen.getByText(/Activity is not inferred from transcripts/)).not.toBeNull();
    expect(screen.queryByText("private activity")).toBeNull();
  });

  it("renders raw markdown as inert text and redacts host paths", () => {
    const raw = "## Objective\n<script>alert('unsafe')</script>\nC:\\Users\\danhm\\secret.txt";
    window.history.replaceState({}, "", "/runs/run-alpha/tickets/A2?fixture=raw-escaped");
    const { container } = render(<TicketInspector snapshot={snapshot({ id: "A2", raw })} location={{ ...location("raw-escaped", "A2"), run: "run-alpha" }} />);
    const code = screen.getByLabelText("Raw ticket markdown").querySelector("code");
    expect(code?.textContent).toContain("<script>alert('unsafe')</script>");
    expect(code?.textContent).toContain("[redacted-path]");
    expect(code?.textContent).not.toContain("danhm");
    expect(container.querySelector("script")).toBeNull();
  });

  it("preserves unknown proof rather than treating missing rows as success", () => {
    const value = snapshot({ verification: { state: "unknown", rows: [] } });
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G1?tab=proof");
    render(<TicketInspector snapshot={value} location={location("")} />);
    expect(screen.getByRole("heading", { name: "Proof unavailable" })).not.toBeNull();
    expect(screen.getByText(/Unknown is preserved/)).not.toBeNull();
  });

  it("renders named deterministic fixture evidence when the fixed reader fixture cannot select a ticket", () => {
    const value = snapshot();
    value.ticket = null;
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G4?fixture=running-overview");
    render(<TicketInspector snapshot={value} location={location("running-overview", "G4")} />);
    expect(screen.getByRole("heading", { name: "G4" })).not.toBeNull();
    expect(screen.getByText(/assigned worker is executing this ticket/i)).not.toBeNull();
    expect(screen.queryByRole("heading", { name: "Ticket unavailable" })).toBeNull();
  });
});
