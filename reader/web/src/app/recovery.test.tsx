import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { ObserveApp } from "../ObserveApp";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it.each([
  ["/now", "Now", null],
  ["/runs/recovery-run", "Execution run", "recovery-run"],
  ["/runs/recovery-run/tickets/R1?tab=report", "Ticket", "R1"],
  ["/workflows", "Workflows", null],
  ["/workflows/evolve", "evolve", "evolve"],
  ["/workflows/evolve/sources/src_test", "evolve source", "src_test"],
  ["/sessions", "Sessions", null],
  ["/sessions/recovery-session", "Agent session", "recovery-session"],
  ["/friction", "Friction", null],
])("keeps context and retries the selected resource at %s", async (href, title, identity) => {
  window.history.replaceState({}, "", href);
  let complete!: (value: Response) => void;
  const fetcher = vi.fn().mockImplementation(() => new Promise<Response>((resolve) => { complete = resolve; }));
  vi.stubGlobal("fetch", fetcher);
  render(<ObserveApp />);
  expect(await screen.findByRole("heading", { level: 1, name: title })).toBeTruthy();
  if (identity) expect(screen.getAllByText(identity).length).toBeGreaterThan(0);
  complete(new Response(null, { status: 503 }));
  const retry = await screen.findByRole("button", { name: "Retry now" });
  const originalUrl = fetcher.mock.calls[0][0];
  await userEvent.click(retry);
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
  expect(fetcher.mock.calls[1][0]).toBe(originalUrl);
  expect(window.location.pathname + window.location.search).toBe(href);
  expect(screen.getByRole("heading", { level: 1, name: title })).toBeTruthy();
  expect(screen.getByRole("link", { name: /^Back to / })).toBeTruthy();
});
