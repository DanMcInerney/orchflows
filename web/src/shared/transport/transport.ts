import { useEffect, useState } from "react";
import type {
  Diagnostic,
  FeatureData,
  FeatureState,
  RequestSpec,
} from "./types";

export interface TransportEnvironment {
  fetcher: (url: string, init: RequestInit) => Promise<Response>;
  schedule: (callback: () => void, delay: number) => unknown;
  cancel: (handle: unknown) => void;
}

export interface PollingTransport<Route, Payload, Model> {
  start(route: Route, data: FeatureData<Route, Payload, Model>): Promise<void>;
  refresh(): Promise<void>;
  stop(): void;
  getState(): FeatureState<Model>;
}

interface PollingTransportOptions<Model> {
  onState: (state: FeatureState<Model>) => void;
  environment?: TransportEnvironment;
}

const LOADING = { status: "loading", model: null, error: null } as const;
const DIAGNOSTICS: Record<Diagnostic["code"], Diagnostic> = {
  "not-found": { code: "not-found", message: "The requested reader resource was not found." },
  "invalid-payload": { code: "invalid-payload", message: "The reader response was invalid." },
  unavailable: { code: "unavailable", message: "The reader response was unavailable." },
};

function defaultEnvironment(): TransportEnvironment {
  return {
    fetcher: (url, init) => fetch(url, init),
    schedule: (callback, delay) => window.setTimeout(callback, delay),
    cancel: (handle) => window.clearTimeout(handle as number),
  };
}

function requestInit(request: RequestSpec, etag: string | null, signal: AbortSignal): RequestInit {
  const headers = new Headers(request.init?.headers);
  if (etag !== null) headers.set("If-None-Match", etag);
  return { ...request.init, headers, cache: request.init?.cache ?? "no-store", signal };
}

export function createPollingTransport<Route, Payload, Model>(
  options: PollingTransportOptions<Model>,
): PollingTransport<Route, Payload, Model> {
  const environment = options.environment ?? defaultEnvironment();
  let state: FeatureState<Model> = LOADING;
  let route: Route | undefined;
  let data: FeatureData<Route, Payload, Model> | undefined;
  let model: Model | null = null;
  let hasModel = false;
  let etag: string | null = null;
  let generation = 0;
  let requestSequence = 0;
  let activeRequest: AbortController | null = null;
  let scheduled: unknown;

  const publish = (next: FeatureState<Model>) => {
    state = next;
    options.onState(next);
  };

  const cancelScheduled = () => {
    if (scheduled !== undefined) {
      environment.cancel(scheduled);
      scheduled = undefined;
    }
  };

  const publishFailure = (diagnostic: Diagnostic) => {
    if (hasModel) {
      publish({ status: "stale", model: model as Model, error: diagnostic });
    } else {
      publish({ status: "error", model: null, error: diagnostic });
    }
  };

  const scheduleNext = () => {
    if (data === undefined) return;
    const policy = data.polling(hasModel ? model : null);
    if (policy === false) return;
    if (!Number.isFinite(policy.intervalMs) || policy.intervalMs < 0) {
      publishFailure(DIAGNOSTICS.unavailable);
      return;
    }
    scheduled = environment.schedule(() => {
      scheduled = undefined;
      void refresh();
    }, policy.intervalMs);
  };

  const refresh = async (): Promise<void> => {
    if (route === undefined || data === undefined) return;
    cancelScheduled();
    activeRequest?.abort();
    const controller = new AbortController();
    activeRequest = controller;
    const currentGeneration = generation;
    const currentRequest = ++requestSequence;
    const currentData = data;
    const currentRoute = route;

    try {
      const request = currentData.request(currentRoute);
      const response = await environment.fetcher(
        request.url,
        requestInit(request, etag, controller.signal),
      );
      if (currentGeneration !== generation || currentRequest !== requestSequence) return;
      etag = response.headers.get("ETag") ?? etag;
      if (response.status === 304) {
        if (!hasModel) publishFailure(DIAGNOSTICS.unavailable);
        return;
      }
      if (response.status === 404) {
        publishFailure(DIAGNOSTICS["not-found"]);
        return;
      }
      if (!response.ok) {
        publishFailure(DIAGNOSTICS.unavailable);
        return;
      }
      try {
        const payload = currentData.schema(await response.json());
        model = currentData.project(payload);
        hasModel = true;
        publish({ status: "ready", model, error: null });
      } catch {
        publishFailure(DIAGNOSTICS["invalid-payload"]);
      }
    } catch {
      if (currentGeneration !== generation || currentRequest !== requestSequence) return;
      publishFailure(DIAGNOSTICS.unavailable);
    } finally {
      if (currentGeneration === generation && currentRequest === requestSequence) {
        activeRequest = null;
        scheduleNext();
      }
    }
  };

  return {
    start(nextRoute, nextData) {
      generation += 1;
      requestSequence += 1;
      activeRequest?.abort();
      activeRequest = null;
      cancelScheduled();
      route = nextRoute;
      data = nextData;
      model = null;
      hasModel = false;
      etag = null;
      publish(LOADING);
      return refresh();
    },
    refresh,
    stop() {
      generation += 1;
      requestSequence += 1;
      activeRequest?.abort();
      activeRequest = null;
      cancelScheduled();
      route = undefined;
      data = undefined;
    },
    getState: () => state,
  };
}

export function usePollingTransport<Route, Payload, Model>(
  route: Route,
  data: FeatureData<Route, Payload, Model>,
): FeatureState<Model> {
  const [state, setState] = useState<FeatureState<Model>>(LOADING);

  useEffect(() => {
    const transport = createPollingTransport<Route, Payload, Model>({ onState: setState });
    void transport.start(route, data);
    return () => transport.stop();
  }, [route, data]);

  return state;
}
