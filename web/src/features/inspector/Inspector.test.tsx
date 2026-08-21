import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { executionTicketRoute } from "../../shared/routes/executionRoutes";
import TicketInspector from "./Inspector";
import type { InspectorModel, TicketDetail } from "./model";
import { route as inspectorRoute } from "./route";

function model(overrides: Partial<TicketDetail> = {}): InspectorModel {
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
    run: null,
    ticket,
  } as InspectorModel;
}

function route(fixture: string, ticket = "G1") {
  return { run: "run-gamma", ticket, fixture };
}

const ready = (value: InspectorModel) => ({ status: "ready", model: value, error: null } as const);

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.history.replaceState({}, "", "/");
});

describe("TicketInspector", () => {
  it("delegates canonical ticket matching and construction to the shared execution route", () => {
    const match = vi.spyOn(executionTicketRoute, "match");
    const build = vi.spyOn(executionTicketRoute, "build");
    const location = { pathname: "/runs/run%20gamma/tickets/G%2F1", search: "?fixture=running-overview", hash: "" };

    expect(inspectorRoute.match(location)).toEqual({ run: "run gamma", ticket: "G/1", fixture: "running-overview" });
    expect(match).toHaveBeenCalledWith(location);
    expect(inspectorRoute.build({ run: "run gamma", ticket: "G/1", fixture: "running-overview" }))
      .toBe("/runs/run%20gamma/tickets/G%2F1?fixture=running-overview");
    expect(build).toHaveBeenCalledWith({ run: "run gamma", ticket: "G/1", fixture: "running-overview" });
  });

  it("opens a direct-linked tab and keeps pointer selection in the URL", async () => {
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G1?fixture=running-overview&tab=proof");
    const { container } = render(<TicketInspector state={ready(model())} route={route("running-overview")} />);

    expect(container.querySelector(".foundation-view.ticket-inspector")).not.toBeNull();
    expect(screen.getByRole("tab", { name: /Proof/ }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByRole("heading", { name: "Criteria and verdicts" })).not.toBeNull();

    await userEvent.click(screen.getByRole("tab", { name: "Details" }));
    expect(screen.getByRole("heading", { name: "Routing and limits" })).not.toBeNull();
    expect(new URLSearchParams(window.location.search).get("tab")).toBe("details");
  });

  it("gives keyboard tab selection the same behavior as pointer selection", async () => {
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G1?fixture=running-overview");
    render(<TicketInspector state={ready(model())} route={route("running-overview")} />);
    const overview = screen.getByRole("tab", { name: "Overview" });
    overview.focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Details" }).getAttribute("aria-selected")).toBe("true");
    expect(new URLSearchParams(window.location.search).get("tab")).toBe("details");
  });

  it("renders passing and failing proof identities without losing oracle evidence", () => {
    const passing = model();
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G1?fixture=proof-pass");
    const { unmount } = render(<TicketInspector state={ready(passing)} route={route("proof-pass")} />);
    expect(screen.getAllByText("PASS")).toHaveLength(3);
    expect(screen.queryByText("FAIL")).toBeNull();
    expect(screen.getByText("install.py --dry-run")).not.toBeNull();
    expect(screen.getByText("plan named 4 scripts, 4 expected")).not.toBeNull();
    unmount();

    const failing = model();
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G1?fixture=proof-fail");
    render(<TicketInspector state={ready(failing)} route={route("proof-fail")} />);
    expect(screen.getByText("FAIL")).not.toBeNull();
    expect(screen.getByLabelText("Ticket state: failed")).not.toBeNull();
    expect(screen.getByText("Criterion 3 failed")).not.toBeNull();
    expect(screen.getByText(/install.py --dry-run: plan named 3 scripts/)).not.toBeNull();
    expect(screen.getAllByText("deterministic", { selector: "span" })).toHaveLength(3);
  });

  it("shows only friction linked by both run and ticket", () => {
    const value = model();
    if (!value.ticket) throw new Error("fixture ticket missing");
    value.ticket.linked_friction = [
      { ts: "2026-08-01T00:00:00Z", run: "run-gamma", ticket: "G1", category: "contract-gap", observed: "Linked observation", expected: "Linked expectation", host: "fixture" },
      { ts: "2026-08-02T00:00:00Z", run: "run-gamma", ticket: "G2", category: "workaround", observed: "Other ticket", expected: "Not shown", host: "fixture" }
    ];
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G1?fixture=friction-present");
    render(<TicketInspector state={ready(value)} route={route("friction-present")} />);
    expect(screen.getByText("Linked observation")).not.toBeNull();
    expect(screen.queryByText("contract-gap")).toBeNull();
    expect(screen.queryByText("Other ticket")).toBeNull();
  });

  it("states that history is unavailable instead of inferring transcript activity", () => {
    const value = model({ history: [{ ts: "2026-08-01", event: "tool_pre", agent: "worker", detail: "private activity" }] });
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G7?fixture=history-unavailable");
    render(<TicketInspector state={ready(value)} route={route("history-unavailable", "G7")} />);
    expect(screen.getByRole("heading", { name: "History unavailable" })).not.toBeNull();
    expect(screen.getByText(/Activity is not inferred from transcripts/)).not.toBeNull();
    expect(screen.queryByText("private activity")).toBeNull();
  });

  it("renders raw markdown as inert text and redacts host paths", () => {
    const raw = "## Objective\n<script>alert('unsafe')</script>\nC:\\Users\\danhm\\secret.txt";
    window.history.replaceState({}, "", "/runs/run-alpha/tickets/A2?fixture=raw-escaped");
    const { container } = render(<TicketInspector state={ready(model({ id: "A2", raw }))} route={{ ...route("raw-escaped", "A2"), run: "run-alpha" }} />);
    const code = screen.getByLabelText("Raw ticket markdown").querySelector("code");
    expect(code?.textContent).toContain("<script>alert('unsafe')</script>");
    expect(code?.textContent).toContain("[redacted-path]");
    expect(code?.textContent).not.toContain("danhm");
    expect(container.querySelector("script")).toBeNull();
  });

  it("preserves unknown proof rather than treating missing rows as success", () => {
    const value = model({ verification: { state: "unknown", rows: [] } });
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G1?tab=proof");
    render(<TicketInspector state={ready(value)} route={route("")} />);
    expect(screen.getByRole("heading", { name: "Proof unavailable" })).not.toBeNull();
    expect(screen.getByText(/Unknown is preserved/)).not.toBeNull();
  });

  it("links the executor source only from an explicit canonical association", () => {
    const value = model({
      executor: "orch-tdd",
      executor_source: {
        state: "available",
        workflow_id: "evolve/code pack",
        source_id: "skill:orch-tdd",
        label: "orch-tdd skill source"
      }
    });
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G1?tab=details");
    const { unmount } = render(<TicketInspector state={ready(value)} route={route("")} />);
    const source = screen.getByRole("link", { name: "Open canonical orch-tdd skill source" });
    expect(source.getAttribute("href")).toBe("/workflows/evolve%2Fcode%20pack/sources/skill%3Aorch-tdd");
    unmount();

    const unavailable = model({
      executor: "orch-tdd",
      executor_source: {
        state: "unavailable",
        reason: "No canonical workflow association was recorded."
      }
    });
    render(<TicketInspector state={ready(unavailable)} route={route("")} />);
    expect(screen.getByText("Executor source unavailable")).not.toBeNull();
    expect(screen.getByText("No canonical workflow association was recorded.")).not.toBeNull();
    expect(screen.queryByRole("link", { name: /orch-tdd.*source/i })).toBeNull();
  });

  it("derives contained artifact links from opaque identities and keeps unresolved entries unavailable", () => {
    const value = model({
      id: "G/1",
      artifacts: {
        state: "rows",
        rows: [
          { artifact_id: "7e3f18d02a8d4b52a1c951f0", label: "Coverage report", state: "available", media_type: "text/markdown" },
          { artifact_id: "../outside", label: "Untrusted path", state: "available", media_type: "text/plain" },
          { artifact_id: "", label: "Prose-only result", state: "unavailable", reason: "No canonical structured result identity resolved inside the state sink." }
        ]
      }
    });
    window.history.replaceState({}, "", "/runs/run%20alpha/tickets/G%2F1?tab=artifacts");
    render(<TicketInspector state={ready(value)} route={{ ...route("", "G/1"), run: "run alpha" }} />);

    const artifact = screen.getByRole("link", { name: "Open contained artifact Coverage report" });
    expect(artifact.getAttribute("href")).toBe("/api/v1/runs/run%20alpha/tickets/G%2F1/artifacts/7e3f18d02a8d4b52a1c951f0");
    expect(screen.getByText("Artifact identity unavailable", { selector: "strong" })).not.toBeNull();
    expect(screen.getByText("No canonical structured result identity resolved inside the state sink.")).not.toBeNull();
    expect(screen.queryByRole("link", { name: /Untrusted path/ })).toBeNull();
  });

  it("assembles judgment explanation mechanically and labels absent rationale unavailable", () => {
    const value = model({
      sections: {
        objective: "Keep projected judgment facts exact.",
        result: "Candidate revision recorded.",
        feedback: "[]",
        risks: "[\"compact viewport\"]"
      },
      judgment: {
        rationale_identity: "",
        rationale_state: "unavailable",
        rationale_reason: "No canonical rationale identity was recorded."
      }
    });
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G1?tab=proof");
    render(<TicketInspector state={ready(value)} route={route("")} />);

    expect(screen.getByRole("heading", { name: "Judgment explanation" })).not.toBeNull();
    expect(screen.getByText("Candidate revision recorded.")).not.toBeNull();
    expect(screen.getByText("[]")).not.toBeNull();
    expect(screen.getByText("[\"compact viewport\"]")).not.toBeNull();
    expect(screen.getByText("Rationale unavailable")).not.toBeNull();
    expect(screen.getByText("No canonical rationale identity was recorded.")).not.toBeNull();
    expect(screen.getByText("tools/validate.py")).not.toBeNull();
    expect(screen.getAllByText("deterministic", { selector: "span" })).toHaveLength(2);
  });

  it("makes absent artifact inventory explicit", () => {
    const value = model({
      artifacts: {
        state: "unavailable",
        rows: [],
        reason: "No canonical artifact identities were projected."
      }
    });
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G1?tab=artifacts");
    render(<TicketInspector state={ready(value)} route={route("")} />);
    expect(screen.getByRole("heading", { name: "Artifacts unavailable" })).not.toBeNull();
    expect(screen.getByText("No canonical artifact identities were projected.")).not.toBeNull();
  });

  it("renders named deterministic fixture evidence when the fixed reader fixture cannot select a ticket", () => {
    const value = model();
    value.ticket = null;
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G4?fixture=running-overview");
    render(<TicketInspector state={ready(value)} route={route("running-overview", "G4")} />);
    expect(screen.getByRole("heading", { name: "G4" })).not.toBeNull();
    expect(screen.getByText(/assigned worker is executing this ticket/i)).not.toBeNull();
    expect(screen.queryByRole("heading", { name: "Ticket unavailable" })).toBeNull();
  });
});
