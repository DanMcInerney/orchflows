import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import type { ExperienceSnapshot } from "../../api/schema";
import type { LocationState } from "../../state/location";
import { SessionsView } from "./SessionsView";

const PRIVATE_SENTINEL = "ZQXJVWNTRPKB-transcript-content-must-not-render";
afterEach(cleanup);

function snapshot(items: unknown[], diagnostics: string[] = []): ExperienceSnapshot {
  return {
    schema: "orchflows.experience.v1",
    navigation: [], selection: { view: "sessions", run: "", ticket: "", session: "" },
    runs: [], run: null, ticket: null,
    sessions: { items, diagnostics, empty: items.length === 0 },
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
    expect(screen.getAllByText("Unknown client")).toHaveLength(2);
    expect(screen.getAllByText("Project metadata unavailable")).toHaveLength(2);
    const link = screen.getByRole("link", { name: "Open Index safe session metadata" });
    expect(link.getAttribute("href")).toBe("/sessions/11111111-1111-4111-8111-111111111111");
    await user.tab();
    expect(document.activeElement).toBe(screen.getByRole("searchbox", { name: "Filter sessions by title or identity" }));
    await user.tab();
    expect(document.activeElement).toBe(link);
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
    render(<SessionsView snapshot={snapshot(populated)} location={location("diagnostic")} />);
    expect(screen.getByRole("status").textContent).toContain("Metadata needs attention");
    expect(screen.getByText("unreadable transcript lines: 1")).toBeTruthy();
    expect(screen.getByText("Unknown client")).toBeTruthy();
    expect(screen.queryByText("Codex")).toBeNull();
    expect(screen.queryByText("Claude")).toBeNull();
  });
});
