import { describe, expect, it, vi } from "vitest";
import {
  createPollingTransport,
  type TransportEnvironment,
} from "./transport";
import type { FeatureData, FeatureState } from "./types";

type Route = { id: string };
type Payload = { value: number };
type Model = { id: string; value: number };

const data: FeatureData<Route, Payload, Model> = {
  schema(value) {
    if (!value || typeof value !== "object" || typeof (value as Payload).value !== "number") {
      throw new Error("invalid payload");
    }
    return value as Payload;
  },
  request: ({ id }) => ({ url: `/api/items/${id}`, init: { headers: { Accept: "application/json" } } }),
  polling: () => ({ intervalMs: 25 }),
  project: ({ value }) => ({ id: "projected", value }),
};

function response(status: number, value?: unknown, etag?: string): Response {
  return new Response(value === undefined ? null : JSON.stringify(value), {
    status,
    headers: etag ? { ETag: etag, "Content-Type": "application/json" } : undefined,
  });
}

function environment(fetcher: TransportEnvironment["fetcher"]): TransportEnvironment & {
  scheduled: Array<{ callback: () => void; delay: number }>;
} {
  const scheduled: Array<{ callback: () => void; delay: number }> = [];
  return {
    fetcher,
    scheduled,
    schedule(callback, delay) {
      scheduled.push({ callback, delay });
      return callback;
    },
    cancel: vi.fn(),
  };
}

describe("polling transport", () => {
  it("moves through loading, error, ready, stale, and recovered ready while preserving ETags", async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(response(404))
      .mockResolvedValueOnce(response(200, { value: 1 }, '"one"'))
      .mockResolvedValueOnce(response(200, { wrong: true }))
      .mockResolvedValueOnce(response(503))
      .mockResolvedValueOnce(response(200, { value: 2 }, '"two"'))
      .mockResolvedValueOnce(response(304));
    const states: FeatureState<Model>[] = [];
    const env = environment(fetcher);
    const transport = createPollingTransport<Route, Payload, Model>({
      environment: env,
      onState: (state) => states.push(state),
    });

    await transport.start({ id: "a" }, data);
    expect(states.map(({ status }) => status)).toEqual(["loading", "error"]);
    expect(states.at(-1)).toMatchObject({ error: { code: "not-found" }, model: null });

    await transport.refresh();
    expect(states.at(-1)).toEqual({ status: "ready", model: { id: "projected", value: 1 }, error: null });
    await transport.refresh();
    expect(states.at(-1)).toMatchObject({ status: "stale", error: { code: "invalid-payload" } });
    await transport.refresh();
    expect(states.at(-1)).toMatchObject({ status: "stale", error: { code: "unavailable" } });
    await transport.refresh();
    expect(states.at(-1)).toEqual({ status: "ready", model: { id: "projected", value: 2 }, error: null });

    const stateCount = states.length;
    await transport.refresh();
    expect(states).toHaveLength(stateCount);
    expect(env.scheduled.at(-1)?.delay).toBe(25);

    const secondRequestHeaders = new Headers(fetcher.mock.calls[2][1]?.headers);
    expect(secondRequestHeaders.get("Accept")).toBe("application/json");
    expect(secondRequestHeaders.get("If-None-Match")).toBe('"one"');
  });

  it("aborts and invalidates an older route generation before it can overwrite the new route", async () => {
    let resolveOld!: (value: Response) => void;
    let resolveNew!: (value: Response) => void;
    const oldResponse = new Promise<Response>((resolve) => { resolveOld = resolve; });
    const newResponse = new Promise<Response>((resolve) => { resolveNew = resolve; });
    const fetcher = vi.fn()
      .mockReturnValueOnce(oldResponse)
      .mockReturnValueOnce(newResponse);
    const states: FeatureState<Model>[] = [];
    const env = environment(fetcher);
    const transport = createPollingTransport<Route, Payload, Model>({
      environment: env,
      onState: (state) => states.push(state),
    });

    const oldPoll = transport.start({ id: "old" }, { ...data, polling: () => false });
    const oldSignal = fetcher.mock.calls[0][1]?.signal;
    const newPoll = transport.start({ id: "new" }, {
      ...data,
      polling: () => false,
      project: ({ value }) => ({ id: "new", value }),
    });

    expect(oldSignal?.aborted).toBe(true);
    resolveNew(response(200, { value: 2 }));
    await newPoll;
    resolveOld(response(200, { value: 1 }));
    await oldPoll;

    expect(states.at(-1)).toEqual({ status: "ready", model: { id: "new", value: 2 }, error: null });
    expect(states).not.toContainEqual({ status: "ready", model: { id: "projected", value: 1 }, error: null });
  });
});
