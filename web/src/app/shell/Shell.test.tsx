import { act, cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { matchCatalog } from "../catalog";
import { featureCatalog } from "./featureCatalog";
import { Shell } from "./Shell";

function location(pathname: string, search = "") {
  return { pathname, search, hash: "" };
}

describe("application feature catalog", () => {
  it("fixes rail order and binds canonical hidden routes to their parent", () => {
    const rail = featureCatalog.flatMap((entry) => {
      if (entry.kind === "disabled") return [entry.navigation.label];
      return entry.navigation === false ? [] : [entry.navigation.label];
    });

    expect(rail).toEqual(["Now", "Workflows", "Create", "Sessions", "Friction"]);
    expect(featureCatalog.find((entry) => entry.id === "create")).toMatchObject({
      kind: "disabled",
      navigation: { label: "Create" },
    });

    expect(matchCatalog(featureCatalog, location("/runs/run%20alpha/tickets/T-1/"))).toMatchObject({
      id: "ticket",
      activeNavigationId: "workflows",
      canonicalHref: "/runs/run%20alpha/tickets/T-1",
      isCanonical: false,
    });
    expect(matchCatalog(featureCatalog, location("/sessions/session%20alpha"))).toMatchObject({
      id: "session-graph",
      activeNavigationId: "sessions",
      canonicalHref: "/sessions/session%20alpha",
      isCanonical: true,
    });
  });
});

describe("catalog-bound shell", () => {
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("renders the fixed rail, canonicalizes refresh, and polls only the mounted host", async () => {
    window.history.replaceState({}, "", "/now/");
    const requests: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (request: string | URL | Request) => {
      const url = String(request);
      requests.push(url);
      if (url === "/api/v1/views/sessions") {
        return response({ schema: "orchflows.sessions.v1", sessions: { items: [], diagnostics: [], empty: true } });
      }
      return response({ schema: "orchflows.now.v1", runs: [] });
    }));

    render(<Shell />);

    expect(await screen.findByRole("heading", { level: 1, name: "Now" })).toBeTruthy();
    await waitFor(() => expect(window.location.pathname).toBe("/now"));
    const rail = screen.getByRole("navigation", { name: "Observe views" });
    expect(within(rail).getAllByRole("link").map((link) => link.textContent)).toEqual([
      "Now", "Workflows", "Sessions", "Friction",
    ]);
    expect(within(rail).getByText("Create").closest("[aria-disabled='true']")).toBeTruthy();
    expect(requests).toEqual(["/api/v1/views/now"]);

    await userEvent.click(within(rail).getByRole("link", { name: "Sessions" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Sessions" })).toBeTruthy();
    expect(window.location.pathname).toBe("/sessions");
    expect(requests).toEqual(["/api/v1/views/now", "/api/v1/views/sessions"]);
  });

  it("refreshes a hidden deep link with its parent highlighted and no fallback route", async () => {
    window.history.replaceState({}, "", "/runs/run%20alpha/tickets/T-1/");
    vi.stubGlobal("fetch", vi.fn(async () => response({
      schema: "orchflows.inspector.v1",
      run: null,
      ticket: null,
    })));

    const { unmount } = render(<Shell />);

    const workflows = await screen.findByRole("link", { name: "Workflows" });
    expect(workflows.getAttribute("aria-current")).toBe("page");
    await waitFor(() => expect(window.location.pathname).toBe("/runs/run%20alpha/tickets/T-1"));
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "/api/v1/views/inspector?run=run+alpha&ticket=T-1",
      expect.anything(),
    );

    unmount();
    window.history.replaceState({}, "", "/not-a-reader-route");
    render(<Shell />);
    expect(screen.getByRole("heading", { name: "View not found" })).toBeTruthy();
    expect(screen.queryByRole("link", { current: "page" })).toBeNull();
  });

  it("keeps the last safe model stale and then recovers on a later poll", async () => {
    await import("../../features/friction/FrictionView");
    vi.useFakeTimers();
    window.history.replaceState({}, "", "/friction");
    let call = 0;
    vi.stubGlobal("fetch", vi.fn(async () => {
      call += 1;
      if (call === 2) return new Response(null, { status: 503 });
      return response({
        schema: "orchflows.friction.v1",
        friction: {
          items: [{ observed: call === 1 ? "Initial safe record" : "Recovered safe record" }],
          skipped: 0,
          unreadable: 0,
        },
      });
    }));

    render(<Shell />);
    await act(async () => { await vi.advanceTimersByTimeAsync(0); });
    expect(screen.getByRole("heading", { name: "Initial safe record" })).toBeTruthy();

    await act(async () => { await vi.advanceTimersByTimeAsync(2500); });
    expect(screen.getByText("The reader response was unavailable.")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Initial safe record" })).toBeTruthy();

    await act(async () => { await vi.advanceTimersByTimeAsync(2500); });
    expect(screen.getByRole("heading", { name: "Recovered safe record" })).toBeTruthy();
    expect(screen.queryByText("The reader response was unavailable.")).toBeNull();
  });
});

function response(value: unknown): Response {
  return new Response(JSON.stringify(value), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
