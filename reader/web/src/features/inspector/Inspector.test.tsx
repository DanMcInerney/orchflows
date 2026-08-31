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
    sections: { goal: "Prove the inspector without exposing private activity." },
    report: "The safe recorded report.",
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
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G1?fixture=running-overview&tab=report");
    const { container } = render(<TicketInspector state={ready(model())} route={route("running-overview")} />);

    expect(container.querySelector(".foundation-view.ticket-inspector")).not.toBeNull();
    expect(screen.getByRole("tab", { name: /Report/ }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByRole("heading", { name: "Recorded report" })).not.toBeNull();

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

  it("renders a recorded report as one inert body without parsing anything out of it", () => {
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G1?fixture=report-recorded");
    const { container } = render(<TicketInspector state={ready(model())} route={route("report-recorded")} />);
    const body = screen.getByLabelText("Recorded report");
    expect(body.textContent).toContain("Gate replayed at the tip");
    expect(body.textContent).toContain("the one executor filing");
    expect(container.querySelector(".report-section")).toBeNull();
    expect(screen.getByLabelText("Ticket state: complete")).not.toBeNull();
  });

  it("shows an earlier-grammar ticket's recorded sections as written instead of reviving their parsing", () => {
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G1?fixture=report-historical");
    const { container } = render(<TicketInspector state={ready(model())} route={route("report-historical")} />);
    expect(screen.getByLabelText("Ticket state: failed")).not.toBeNull();
    expect(screen.getByText(/earlier five-section grammar/)).not.toBeNull();
    const names = Array.from(container.querySelectorAll(".report-section h3")).map((node) => node.textContent);
    expect(names).toEqual(["Result", "Verification", "Feedback", "Risks"]);
    const verification = container.querySelectorAll(".report-section__body")[1];
    expect(verification?.textContent).toContain("| 2 | FAIL | install.py --dry-run | deterministic | plan named 3 scripts, 4 expected |");
    expect(container.querySelector(".report-body")).toBeNull();
  });

  it("renders live historical sections from the projection when the report is absent", () => {
    const value = model({
      report: "",
      sections: {
        goal: "Keep the recorded sections exact.",
        result: "Candidate revision recorded.",
        feedback: "[]",
        risks: "[\"compact viewport\"]"
      }
    });
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G1?tab=report");
    const { container } = render(<TicketInspector state={ready(value)} route={route("")} />);

    const names = Array.from(container.querySelectorAll(".report-section h3")).map((node) => node.textContent);
    expect(names).toEqual(["Result", "Feedback", "Risks"]);
    expect(screen.getByText("Candidate revision recorded.")).not.toBeNull();
    expect(screen.getByText("[]")).not.toBeNull();
    expect(screen.getByText("[\"compact viewport\"]")).not.toBeNull();
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
    const raw = "## Goal\n<script>alert('unsafe')</script>\nC:\\Users\\danhm\\secret.txt";
    window.history.replaceState({}, "", "/runs/run-alpha/tickets/A2?fixture=raw-escaped");
    const { container } = render(<TicketInspector state={ready(model({ id: "A2", raw }))} route={{ ...route("raw-escaped", "A2"), run: "run-alpha" }} />);
    const code = screen.getByLabelText("Raw ticket markdown").querySelector("code");
    expect(code?.textContent).toContain("<script>alert('unsafe')</script>");
    expect(code?.textContent).toContain("[redacted-path]");
    expect(code?.textContent).not.toContain("danhm");
    expect(container.querySelector("script")).toBeNull();
  });

  it("preserves an absent report rather than presenting it as an empty success", () => {
    const value = model({ report: "", sections: { goal: "No filing yet." } });
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G1?tab=report");
    render(<TicketInspector state={ready(value)} route={route("")} />);
    expect(screen.getByRole("heading", { name: "Report unavailable" })).not.toBeNull();
    expect(screen.getByText(/Absence is preserved/)).not.toBeNull();
  });

  it("shows the planner's Context and Details prose on the details tab as written", () => {
    const value = model({
      sections: {
        goal: "Keep the brief visible.",
        context: "- the accepted projection is the only input",
        details: "- scratch/g1.txt"
      }
    });
    window.history.replaceState({}, "", "/runs/run-gamma/tickets/G1?tab=details");
    const { container } = render(<TicketInspector state={ready(value)} route={route("")} />);
    const names = Array.from(container.querySelectorAll(".report-section h3")).map((node) => node.textContent);
    expect(names).toEqual(["Context", "Details"]);
    expect(screen.getByText("- the accepted projection is the only input")).not.toBeNull();
    expect(screen.getByText("- scratch/g1.txt")).not.toBeNull();
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
