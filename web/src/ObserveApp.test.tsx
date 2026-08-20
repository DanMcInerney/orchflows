import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ObserveApp } from "./ObserveApp";

describe("ObserveApp", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("delegates the read-only experience to the catalog-bound shell", async () => {
    window.history.replaceState({}, "", "/now");
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      schema: "orchflows.now.v1",
      runs: [],
    }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    })));

    render(<ObserveApp />);

    expect(await screen.findByRole("heading", { level: 1, name: "Now" })).toBeTruthy();
    expect(document.querySelector("main[data-mode='observe']")).not.toBeNull();
    expect(screen.getByText("read only")).toBeTruthy();
    const rail = screen.getByRole("navigation", { name: "Observe views" });
    expect(within(rail).getByText("Create").closest("[aria-disabled='true']")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /start|edit|delete/i })).toBeNull();
    expect(vi.mocked(fetch)).toHaveBeenCalledWith("/api/v1/views/now", expect.anything());
    expect(vi.mocked(fetch).mock.calls.flat().join(" ")).not.toContain("/api/v1/experience");
  });
});
