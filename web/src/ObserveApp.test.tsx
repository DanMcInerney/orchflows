import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ObserveApp } from "./ObserveApp";

vi.mock("./graph/RunGraph", () => ({
  RunGraph: ({ tickets }: { tickets: unknown[] }) => <div data-testid="run-graph">{tickets.length} projected tickets</div>
}));

const base = {
  schema: "orchflows.experience.v1",
  navigation: [
    { id: "now", label: "Now", path: "/now", disabled: false, explanation: "" },
    { id: "run-map", label: "Workflows", path: "/runs", disabled: false, explanation: "" },
    { id: "create", label: "Create", path: "", disabled: true, explanation: "Future workflow authoring is unavailable in this read-only observer." },
    { id: "sessions", label: "Sessions", path: "/sessions", disabled: false, explanation: "" },
    { id: "friction", label: "Friction", path: "/friction", disabled: false, explanation: "" }
  ],
  selection: { view: "now", run: "run-alpha", ticket: "", session: "" },
  runs: [{ id: "run-alpha", ticket_count: 1, active: true }],
  run: {
    id: "run-alpha", active: true, counts: { claimed: 1 },
    tickets: [{
      id: "A1", status: "claimed", executor: "orch-render", bound: "90m",
      claimed_at: "", claimed_by: "", depends_on: [], unreadable: false,
      readiness: { state: "running", dependencies: [], explanation: "A1 is claimed" }
    }]
  },
  ticket: null,
  sessions: { items: [], diagnostics: [], empty: true },
  session: null,
  friction: { items: [], skipped: 0, unreadable: 0 }
};

describe("ObserveApp foundation", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    window.history.replaceState({}, "", "/now?fixture=mixed-live");
    let call = 0;
    vi.stubGlobal("fetch", vi.fn(async () => {
      call += 1;
      if (call === 2) return new Response(null, { status: 304, headers: { ETag: '"one"' } });
      return new Response(JSON.stringify(base), {
        status: 200, headers: { "Content-Type": "application/json", ETag: '"one"' }
      });
    }));
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("keeps a safe ETag feed behind a semantic read-only shell", async () => {
    render(<ObserveApp />);
    await act(async () => { await Promise.resolve(); await Promise.resolve(); await Promise.resolve(); });
    expect(screen.getByRole("main").getAttribute("data-mode")).toBe("observe");
    expect(screen.getByText("read only")).not.toBeNull();
    expect(screen.getByText("Workflows")).not.toBeNull();
    expect(screen.getByText("future")).not.toBeNull();
    expect(screen.getByRole("heading", { name: "Work is moving across three runs" })).not.toBeNull();
    expect(screen.getByTestId("run-graph").textContent).toBe("3 projected tickets");
    expect(screen.queryByRole("button", { name: /start|edit|delete/i })).toBeNull();
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain("/api/v1/experience?view=now");
    await vi.advanceTimersByTimeAsync(750);
    expect(vi.mocked(fetch).mock.calls[1][1]).toMatchObject({ headers: { "If-None-Match": '"one"' } });
  });
});
