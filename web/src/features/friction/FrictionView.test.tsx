import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { FrictionView } from "./FrictionView";
import { closedFrictionRecord, frictionModel, type FrictionModel } from "./model";

const route = { fixture: "populated" };

afterEach(cleanup);

function model(items: unknown[], skipped = 0, unreadable = 0): FrictionModel {
  return frictionModel({ items, skipped, unreadable });
}

const ready = (value: FrictionModel) => ({ status: "ready", model: value, error: null } as const);

describe("FrictionView", () => {
  it("renders safe diagnostics with exact run and ticket linkage", () => {
    const { container } = render(<FrictionView state={ready(model([{
      ts: "2026-08-19T04:42:03Z",
      category: "contract-gap",
      host: "codex",
      observed: "The verifier could not connect the view outlet",
      expected: "The feature module should be discoverable",
      run: "run / alpha",
      ticket: "00-ui.07",
    }], 1, 2))} route={route} />);

    expect(screen.getByRole("heading", { name: "Some log records need attention" })).not.toBeNull();
    expect(screen.getByText(/2 unreadable records and 1 skipped line/)).not.toBeNull();
    expect(screen.getByRole("heading", { name: "The verifier could not connect the view outlet" })).not.toBeNull();
    expect(screen.getByText("The feature module should be discoverable")).not.toBeNull();
    expect(screen.getByRole("link", { name: /Run run \/ alpha/ }).getAttribute("href")).toBe("/runs/run%20%2F%20alpha");
    expect(screen.getByRole("link", { name: /Ticket 00-ui\.07/ }).getAttribute("href")).toBe("/runs/run%20%2F%20alpha/tickets/00-ui.07");
    expect(screen.queryByRole("button")).toBeNull();
    expect(container.querySelector("form, input, textarea, select")).toBeNull();
    expect(container.querySelector(".friction-view.foundation-view")).not.toBeNull();
  });

  it("escapes markup, redacts host paths, and drops every field outside the closed projection", () => {
    const { container } = render(<FrictionView state={ready(model([{
      ts: "2026-08-19T04:42:03Z",
      category: "<b>markup</b>",
      host: "C:\\Users\\operator\\private",
      observed: "A file at /home/operator/secrets.txt contained <script>unsafe()</script>",
      expected: "Render it as inert text",
      prompt: "PROMPT_SENTINEL",
      tool_input: "TOOL_INPUT_SENTINEL",
      tool_output: "TOOL_OUTPUT_SENTINEL",
      file_contents: "FILE_SENTINEL",
      command_output: "COMMAND_SENTINEL",
      conversation: "CONVERSATION_SENTINEL",
    }]))} route={route} />);

    expect(screen.getByText("<b>markup</b>")).not.toBeNull();
    expect(screen.getByText(/A file at \[redacted path\] contained <script>unsafe\(\)<\/script>/)).not.toBeNull();
    expect(screen.getByText("[redacted path]")).not.toBeNull();
    expect(container.querySelector("script, b")).toBeNull();
    for (const sentinel of ["PROMPT_SENTINEL", "TOOL_INPUT_SENTINEL", "TOOL_OUTPUT_SENTINEL", "FILE_SENTINEL", "COMMAND_SENTINEL", "CONVERSATION_SENTINEL"]) {
      expect(container.textContent).not.toContain(sentinel);
    }
  });

  it("shows an honest empty state for the empty identity", () => {
    render(<FrictionView state={ready(model([{ observed: "would otherwise render" }], 4, 3))} route={{ fixture: "empty" }} />);

    expect(screen.getByRole("heading", { name: "No friction records available" })).not.toBeNull();
    expect(screen.getByLabelText("0 friction records")).not.toBeNull();
    expect(screen.queryByText("would otherwise render")).toBeNull();
    expect(screen.queryByRole("heading", { name: "Some log records need attention" })).toBeNull();
  });

  it("makes exact linked navigation visible in the populated capture fixture", () => {
    render(<FrictionView state={ready(model([{ observed: "Canonical unlinked record" }]))} route={route} />);

    expect(screen.getByRole("link", { name: "Run run-gamma" }).getAttribute("href")).toBe("/runs/run-gamma");
    expect(screen.getByRole("link", { name: "Ticket G1" }).getAttribute("href")).toBe("/runs/run-gamma/tickets/G1");
    expect(screen.getByRole("heading", { name: "Canonical unlinked record" })).not.toBeNull();
  });

  it("keeps incomplete linkage explicit instead of inventing a route", () => {
    render(<FrictionView state={ready(model([
      { observed: "No identifiers" },
      { observed: "Ticket only", ticket: "T7" },
    ]))} route={route} />);

    const first = screen.getByRole("heading", { name: "No identifiers" }).closest("article");
    const second = screen.getByRole("heading", { name: "Ticket only" }).closest("article");
    expect(first && within(first).getByText("No run or ticket recorded")).not.toBeNull();
    expect(second?.textContent).toContain("Ticket T7 (run unavailable)");
    expect(second && within(second).queryByRole("link")).toBeNull();
  });

  it("rejects non-records and preserves only closed string fields", () => {
    expect(closedFrictionRecord(null)).toBeNull();
    expect(closedFrictionRecord(["not", "a", "record"])).toBeNull();
    expect(closedFrictionRecord({ observed: 42, expected: false })).toBeNull();
    expect(closedFrictionRecord({ observed: "kept", extra: "dropped" })).toEqual({ observed: "kept" });
  });

  it("mounts a bounded initial window and reveals more without losing the canonical total", async () => {
    const user = userEvent.setup();
    const items = Array.from({ length: 130 }, (_, index) => ({ observed: `Record ${index + 1}` }));
    const { container } = render(<FrictionView state={ready(model(items))} route={{ fixture: "" }} />);

    expect(screen.getByLabelText("130 friction records")).not.toBeNull();
    expect(container.querySelectorAll(".friction-record")).toHaveLength(50);
    expect(screen.getByText("Showing 50 of 130 records")).not.toBeNull();
    await user.click(screen.getByRole("button", { name: "Show 50 more friction records" }));
    expect(container.querySelectorAll(".friction-record")).toHaveLength(100);
    expect(screen.getByText("Showing 100 of 130 records")).not.toBeNull();
  });
});
