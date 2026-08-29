import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import NowView from "./NowView";
import type { NowModel } from "./model";
import { nowFixture } from "./fixtures";

afterEach(cleanup);

const empty = { status: "ready", model: { runs: [] } as NowModel, error: null } as const;

function headings(container: HTMLElement, selector: string): string[] {
  return [...container.querySelectorAll(selector)].map((node) => node.textContent ?? "");
}

function card(runId: string): HTMLElement {
  return screen.getByLabelText(`Summary flow for ${runId}`).closest(".now-run-card") as HTMLElement;
}

describe("Now folder hierarchy", () => {
  it("puts running sessions above past sessions, each grouped by its folder leaf", () => {
    const { container } = render(<NowView state={empty} route={{ fixture: "mixed-live" }} />);
    const bands = headings(container, "h2");
    expect(bands).toEqual(["Running now", "Past sessions"]);

    const running = screen.getByRole("region", { name: "Running now" });
    const past = screen.getByRole("region", { name: "Past sessions" });
    expect(running.compareDocumentPosition(past) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    expect(headings(running, "h3")).toEqual(["orchflows-public", "atlas-web"]);
    expect(within(running).queryByLabelText(/Summary flow for 20260818-ui-platform/)).toBeNull();
    expect(headings(running, ".now-run-card .now-objective-summary")).toEqual([
      "Restore installed-reader portability across supported hosts",
      "Make live workflow progress legible without exposing conversation content",
      "Cut the first-run onboarding path down to one readable page",
    ]);
  });

  it("orders past folder sections by newest terminal_at descending, not alphabetically", () => {
    const { container } = render(<NowView state={empty} route={{ fixture: "mixed-live" }} />);
    const past = screen.getByRole("region", { name: "Past sessions" });
    expect(headings(past, "h3")).toEqual(["orchflows-public", "ledger-service"]);
    expect([...headings(past, "h3")].sort()).not.toEqual(headings(past, "h3"));

    const finished = card("20260818-ui-platform");
    expect(finished.textContent).toContain("complete · 3 tickets · 2026-08-25T09:15:04Z");
    expect(within(finished).getByRole("link", { name: /^Open full run for/ }).getAttribute("href"))
      .toBe("/runs/20260818-ui-platform?fixture=mixed-live");
    expect(card("20260817-ledger-migration").textContent).toContain("limited · 2 tickets · 2026-08-24T20:42:11Z");
    expect(container.querySelector(".now-flow")).toBeNull();
  });

  it("pairs the shared workflows summary flow with the task summary and a run affordance", () => {
    render(<NowView state={empty} route={{ fixture: "mixed-live" }} />);
    const live = card("20260819-ui-experience");

    const flow = within(live).getByLabelText("Summary flow for 20260819-ui-experience");
    expect(flow.classList.contains("workflow-summary")).toBe(true);
    expect([...flow.querySelectorAll(".workflow-summary__node b")].map((node) => node.textContent))
      .toEqual(["Brief", "Plan", "Work ×3", "Review", "Verify"]);
    expect([...flow.querySelectorAll(".workflow-summary__node")].map((node) => node.getAttribute("data-state")))
      .toEqual(["complete", "complete", "running", "waiting", "waiting"]);
    expect(within(flow).getByLabelText("Nonvisual summary for 20260819-ui-experience").textContent)
      .toContain("Step: Work ×3; running");

    expect(live.querySelector(".now-run-card__task")?.textContent)
      .toBe("Working on Render the live fleet, Render dependency maps");
    expect(within(live).getByRole("link", { name: "Open ticket: Render dependency maps" }).getAttribute("href"))
      .toBe("/runs/20260819-ui-experience/tickets/03-workflows?fixture=mixed-live");

    const open = within(live).getByRole("link", { name: /^Open live workflow for/ });
    expect(open.getAttribute("href")).toBe("/runs/20260819-ui-experience?fixture=mixed-live");
    expect(open.classList.contains("now-run-card__open")).toBe(true);
  });

  it("keeps unrecorded folders and unreadable runs explicit instead of grouping them away", () => {
    render(<NowView state={empty} route={{ fixture: "unreadable-data" }} />);
    const running = screen.getByRole("region", { name: "Running now" });
    expect(headings(running, "h3")).toEqual(["Folder unrecorded"]);
    expect(within(running).getByText("Unknown progress")).toBeTruthy();
    expect(within(running).getByRole("link", { name: "Open run: Run metadata could not be safely projected" })
      .getAttribute("href")).toBe("/runs/unreadable-run?fixture=unreadable-data");
    expect(within(running).queryByLabelText(/Summary flow for unreadable-run/)).toBeNull();
  });

  it("counts the visible fleet in one hero summary and folds a past-only fleet below", () => {
    render(<NowView state={empty} route={{ fixture: "no-active-runs" }} />);
    const summary = screen.getByLabelText("Now summary");
    expect(summary.textContent).toBe("Running0Folders2Finished2");
    expect(screen.getByText("No session is running")).toBeTruthy();
    expect(headings(screen.getByRole("region", { name: "Past sessions" }), "h3"))
      .toEqual(["orchflows-public", "ledger-service"]);
    expect(nowFixture("no-active-runs").runs.every((run) => run.terminalAt)).toBe(true);
  });
});
