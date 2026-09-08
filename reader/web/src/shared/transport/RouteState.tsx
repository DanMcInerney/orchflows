import { ArrowLeft, RefreshCw } from "lucide-react";
import type { FeatureState } from "./types";
import "./route-state.css";

export interface RouteContext {
  title: string;
  identity?: string;
  description: string;
  parents: Array<{ label: string; href: string }>;
  failure?: { title: string; message: string };
}

/** Feature-owned context stays visible while the feature-blind transport recovers. */
export function RouteState({ context, state }: { context: RouteContext; state: FeatureState<unknown> }) {
  const back = context.parents.at(-1);
  return <section className="foundation-view route-state" data-reader-state={state.status}>
    <nav className="route-state__crumbs" aria-label="Breadcrumb">
      {context.parents.map((parent) => <span key={parent.href}><a href={parent.href}>{parent.label}</a><span aria-hidden="true"> / </span></span>)}
      <span aria-current="page">{context.identity || context.title}</span>
    </nav>
    <header><p className="eyebrow">Read-only observer</p><h1>{context.title}</h1><p>{context.description}</p></header>
    <section className="route-state__body" aria-label="Reader availability">
      <RefreshStatus state={state} failure={context.failure} />
      {back && <a className="route-state__back" href={back.href}><ArrowLeft aria-hidden="true" /> Back to {back.label}</a>}
    </section>
  </section>;
}

export function RefreshStatus({ state, failure }: { state: FeatureState<unknown>; failure?: RouteContext["failure"] }) {
  if (state.status === "ready") return null;
  const pending = state.status === "loading" || state.refreshing;
  return <div className="refresh-status" data-reader-state={state.status}>
    <div role="status">
      <h2>{pending ? "Checking reader…" : failure?.title || (state.status === "stale" ? "Refresh failed" : "Reader unavailable")}</h2>
      {state.status === "stale" && <p>Showing the last successful read.</p>}
      <p>{failure?.message || state.error?.message || "Your selected view will appear when its data arrives."}</p>
      <p>{pending ? "Request in progress." : state.autoRefresh ? "Automatic retry is enabled." : "Retry to request this view again."}</p>
    </div>
    {state.status !== "loading" && <button type="button" disabled={Boolean(state.refreshing)} onClick={() => state.refresh ? void state.refresh() : window.location.reload()}>
      <RefreshCw aria-hidden="true" />{state.refreshing ? "Retrying…" : "Retry now"}
    </button>}
  </div>;
}
