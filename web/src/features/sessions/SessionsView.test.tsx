import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import type { ExperienceSnapshot, SessionSummary } from "../../api/schema";
import type { LocationState } from "../../state/location";
import { SessionsView } from "./SessionsView";

const PRIVATE_SENTINEL = "ZQXJVWNTRPKB-transcript-content-must-not-render";
afterEach(cleanup);

function snapshot(items: unknown[], diagnostics: string[] = []): ExperienceSnapshot {
  return {
    schema: "orchflows.experience.v1",
    navigation: [], selection: { view: "sessions", run: "", ticket: "", session: "" },
    runs: [], run: null, ticket: null,
    sessions: { items: items as SessionSummary[], diagnostics, empty: items.length === 0 },
    session: null, friction: { items: [], skipped: 0, unreadable: 0 }
  };
}

function location(fixture: string): LocationState {
  return { view: "sessions", run: "", ticket: "", session: "", fixture };
}

const populated = [
  {
    id: "11111111-1111-4111-8111-111111111111",
    title: "Index safe session metadata",
    modified: "2026-08-19T09:00:00Z",
    agent_count: 2,
    diagnostics: [],
    client: "Claude Code",
    project: "orchflows",
    provider: PRIVATE_SENTINEL,
    cwd: `C:/private/${PRIVATE_SENTINEL}`,
    prompt: PRIVATE_SENTINEL,
    tool_output: PRIVATE_SENTINEL,
    conversation: PRIVATE_SENTINEL
  },
  {
    id: "55555555-5555-4555-8555-555555555555",
    title: "Unreadable metadata stays explicit",
    modified: "",
    agent_count: 0,
    diagnostics: ["unreadable transcript lines: 1"]
  }
];

describe("SessionsView", () => {
  it("renders populated safe metadata, honest unknown clients, and semantic selection", async () => {
    const user = userEvent.setup();
    render(<SessionsView snapshot={snapshot(populated)} location={location("populated")} />);

    expect(screen.getByRole("heading", { name: "Sessions", level: 1 })).toBeTruthy();
    expect(document.querySelector("[data-view='sessions']")?.classList.contains("foundation-view")).toBe(true);
    expect(screen.getByText("Claude Code")).toBeTruthy();
    expect(screen.getByText("orchflows")).toBeTruthy();
    expect(screen.getByText("Unknown client")).toBeTruthy();
    expect(screen.getByText("Unknown project")).toBeTruthy();
    expect(document.querySelectorAll("[data-state='ready']")).toHaveLength(2);
    expect(document.querySelectorAll("[data-unknown]")).toHaveLength(1);
    const link = screen.getByRole("link", { name: "Open Index safe session metadata" });
    expect(link.getAttribute("href")).toBe("/sessions/11111111-1111-4111-8111-111111111111");
    await user.tab();
    expect(document.activeElement).toBe(screen.getByRole("searchbox", { name: "Filter sessions by title or identity" }));
    await user.tab();
    expect(document.activeElement).toBe(link);
    expect(screen.getAllByText("Metadata ready")).toHaveLength(2);
    expect(document.querySelectorAll("[data-state='ready'] svg")).toHaveLength(2);
    expect(screen.queryByRole("status")).toBeNull();
    expect(screen.getByText("2026-08-19 09:00Z").getAttribute("title")).toBe("2026-08-19T09:00:00Z");
    expect(document.body.textContent).not.toContain(PRIVATE_SENTINEL);
  });

  it("filters only on the projected title and identity", async () => {
    const user = userEvent.setup();
    render(<SessionsView snapshot={snapshot(populated)} location={location("populated")} />);
    await user.type(screen.getByRole("searchbox", { name: "Filter sessions by title or identity" }), "55555555");
    expect(screen.queryByText("Index safe session metadata")).toBeNull();
    expect(screen.getByText("Unreadable metadata stays explicit")).toBeTruthy();
  });

  it("renders the explicit empty identity without session affordances", () => {
    render(<SessionsView snapshot={snapshot(populated)} location={location("empty")} />);
    expect(screen.getByRole("status").textContent).toContain("No sessions discovered");
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.queryByRole("searchbox")).toBeNull();
  });

  it("renders diagnostic metadata and never upgrades absent provider facts", () => {
    render(<SessionsView snapshot={snapshot(populated, [
      "project directory name is not an encoded path: C--Users-private-project",
      "second raw parser diagnostic that should not be copied into the banner"
    ])} location={location("diagnostic")} />);
    const status = screen.getByRole("status");
    expect(status.textContent).toContain("Metadata needs attention");
    expect(status.textContent).toContain("2 discovery signals");
    expect(status.textContent).not.toContain("C--Users-private-project");
    expect(status.textContent).not.toContain("second raw parser diagnostic");
    expect(status.textContent?.length).toBeLessThan(180);
    expect(status.compareDocumentPosition(screen.getByRole("heading", { name: "Sessions" })) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(document.querySelectorAll("[data-state='attention']")).toHaveLength(1);
    expect(screen.getByText("Unknown client")).toBeTruthy();
    expect(screen.queryByText("Codex")).toBeNull();
    expect(screen.queryByText("Claude")).toBeNull();
  });
});
