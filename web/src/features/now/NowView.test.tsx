import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ExperienceSnapshot } from "../../api/schema";
import NowView from "./NowView";

vi.mock("../../graph/RunGraph", () => ({ RunGraph: () => <div aria-label="Run dependency graph" /> }));
afterEach(cleanup);

const snapshot: ExperienceSnapshot = {
  schema: "orchflows.experience.v1", navigation: [], selection: { view: "now", run: "", ticket: "", session: "" },
  runs: [], run: null, ticket: null, sessions: { items: [], diagnostics: [], empty: true }, session: null,
  friction: { items: [], skipped: 0, unreadable: 0 },
};

describe("Now view", () => {
  it("renders honest bands, exact counts, and reversible expansion", async () => {
    const user = userEvent.setup();
    const { container } = render(<NowView snapshot={snapshot} location={{ view: "now", run: "", ticket: "", session: "", fixture: "mixed-live" }} />);
    expect(container.querySelector(".foundation-view.now-view")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Now" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Needs attention, 1 runs" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Active now, 1 runs" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Recently completed, 1 runs" })).toBeTruthy();
    const brief = screen.getByRole("button", { name: "Brief1" });
    await user.click(brief);
    expect(screen.getByText("Exact child tickets")).toBeTruthy();
    expect(screen.getByText("00-scope")).toBeTruthy();
  });

  it("pauses without losing selection, filter, expansion, or inspector tab", async () => {
    const user = userEvent.setup();
    render(<NowView snapshot={snapshot} location={{ view: "now", run: "", ticket: "", session: "", fixture: "live-paused" }} />);
    expect(screen.getByText("Live paused")).toBeTruthy();
    await user.click(screen.getByRole("tab", { name: "tickets" }));
    await user.click(screen.getByRole("button", { name: "Needs attention" }));
    await user.click(screen.getByRole("button", { name: "Resume live" }));
    expect(screen.getByRole("tab", { name: "tickets" }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByRole("button", { name: "Needs attention" }).getAttribute("aria-pressed")).toBe("true");
  });

  it("keeps empty and unreadable projections explicit", () => {
    render(<NowView snapshot={snapshot} location={{ view: "now", run: "", ticket: "", session: "", fixture: "no-active-runs" }} />);
    expect(screen.getByText("No active runs. Waiting and completed work remains available.")).toBeTruthy();
    cleanup();
    render(<NowView snapshot={snapshot} location={{ view: "now", run: "", ticket: "", session: "", fixture: "unreadable-data" }} />);
    expect(screen.getByText("Unreadable canonical data")).toBeTruthy();
    expect(screen.getByText("Exact graph unavailable")).toBeTruthy();
  });
});
