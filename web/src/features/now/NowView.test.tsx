import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import NowView from "./NowView";
import type { NowModel } from "./model";

afterEach(cleanup);

const ready = (model: NowModel) => ({ status: "ready", model, error: null } as const);
const empty = ready({ runs: [] });

describe("Now view", () => {
  it("renders one folder hierarchy with shared summary flows and native detail links", () => {
    const { container } = render(<NowView state={empty} route={{ fixture: "mixed-live" }} />);
    expect(container.querySelector(".foundation-view.now-view")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Now" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Running now" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Past sessions" })).toBeTruthy();
    expect(screen.getAllByLabelText(/Nonvisual summary for/)).toHaveLength(5);
    expect(screen.getByRole("link", { name: /Open run: Restore installed-reader portability/ }).getAttribute("href"))
      .toBe("/runs/20260819-portability-repair?fixture=mixed-live");
    expect(screen.getByRole("link", { name: /Open ticket: Repair the portability seam/ }).getAttribute("href"))
      .toBe("/runs/20260819-portability-repair/tickets/01-repair?fixture=mixed-live");
    expect(screen.queryByLabelText(/dependency graph/i)).toBeNull();
  });

  it("keeps pause and filter state explicit", async () => {
    const user = userEvent.setup();
    render(<NowView state={empty} route={{ fixture: "live-paused" }} />);
    expect(screen.getByText("Live paused")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Running now" })).toBeTruthy();
    expect(screen.getByText("Render the live fleet")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Needs attention" }));
    expect(screen.getByText("No runs match this filter.")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Past sessions" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Resume live" }));
    expect(screen.getByRole("button", { name: "Needs attention" }).getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByText("Live · checking for changes")).toBeTruthy();
  });

  it("keeps empty, unreadable, and unknown projections explicit", () => {
    render(<NowView state={empty} route={{ fixture: "no-active-runs" }} />);
    expect(screen.getByText("No session is running")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Past sessions" })).toBeTruthy();
    cleanup();
    render(<NowView state={empty} route={{ fixture: "unreadable-data" }} />);
    expect(screen.getByText("Unreadable canonical data")).toBeTruthy();
    expect(screen.getByText("Unknown progress")).toBeTruthy();
    expect(screen.getByText("Canonical ticket data is unavailable; no progress was inferred.")).toBeTruthy();
  });

  it("bounds long objective summaries while preserving deliberate full disclosure", async () => {
    const user = userEvent.setup();
    const objective = "A very long objective ".repeat(180);
    const longModel: NowModel = { runs: [{
      id: "long-run", objective, repository: "orchflows-public", client: "Codex",
      lastActivity: "now", unreadable: false, tickets: [],
    }] };
    const { container } = render(<NowView state={ready(longModel)} route={{ fixture: "" }} />);

    expect(container.querySelectorAll(".now-objective-summary")).toHaveLength(1);
    const disclosure = screen.getByText("Full objective").closest("details");
    expect(disclosure?.hasAttribute("open")).toBe(false);
    await user.click(screen.getByText("Full objective"));
    expect(disclosure?.hasAttribute("open")).toBe(true);
    expect(disclosure?.textContent).toContain(objective);
  });
});
