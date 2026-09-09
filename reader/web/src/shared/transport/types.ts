export interface Diagnostic {
  code: "not-found" | "invalid-payload" | "unavailable";
  message: string;
}

export type FeatureState<Model> = (
  | { status: "loading"; model: null; error: null }
  | { status: "ready"; model: Model; error: null }
  | { status: "stale"; model: Model; error: Diagnostic }
  | { status: "error"; model: null; error: Diagnostic }) & {
    refresh?: () => Promise<void>;
    refreshing?: boolean;
    autoRefresh?: boolean;
  };

export interface RequestSpec {
  url: string;
  init?: Omit<RequestInit, "signal">;
}

export type PollingPolicy = false | { intervalMs: number };

export interface FeatureData<Route, Payload, Model> {
  schema: (value: unknown) => Payload;
  request: (route: Route) => RequestSpec;
  polling: (model: Model | null) => PollingPolicy;
  project: (payload: Payload) => Model;
}
