import { RouteState, RefreshStatus } from "../../../shared/transport/RouteState";
import { ArrowLeft, Code2, LockKeyhole } from "lucide-react";

import type { FeatureState } from "../../../shared/transport/types";
import type { WorkflowSourceModel } from "../model";
import type { WorkflowSourceRoute } from "../route";
import { detailRoute, listRoute } from "../route";
import "../styles.css";

export interface WorkflowSourceViewProps {
  route: WorkflowSourceRoute;
  state: FeatureState<WorkflowSourceModel>;
}

function parentHref(route: WorkflowSourceRoute): string {
  return detailRoute.build({ workflowId: route.workflowId, fixture: route.fixture });
}

function SourceNavigation({ route }: { route: WorkflowSourceRoute }) {
  return (
    <>
      <nav className="workflow-breadcrumbs" aria-label="Breadcrumb" style={{ flexWrap: "wrap" }}>
        <a href={listRoute.build({ fixture: route.fixture })}>Workflows</a>
        <span aria-hidden="true">/</span>
        <a href={parentHref(route)}>{route.workflowId}</a>
        <span aria-hidden="true">/</span>
        <span aria-current="page" style={{ minWidth: 0, overflowWrap: "anywhere" }}>Source</span>
      </nav>
      <a className="workflow-source__back" href={parentHref(route)}><ArrowLeft aria-hidden="true" /> Back to {route.workflowId}</a>
    </>
  );
}

export function WorkflowSourceView({ route, state }: WorkflowSourceViewProps) {
  if (state.status === "loading" || state.status === "error") return <RouteState state={state} context={{
    title: `${route.workflowId} source`, identity: route.sourceId,
    description: "Read-only source for the selected workflow definition.",
    failure: state.error ? {
      "not-found": { title: "Source not found", message: "This opaque source identity is not associated with this workflow." },
      "invalid-payload": { title: "Source is unreadable", message: "Safe source metadata could not be projected for this cataloged identity." },
      unavailable: { title: "Source is unavailable", message: "The source reader is temporarily unavailable. No file details were exposed." },
    }[state.error.code] : undefined,
    parents: [{ label: "Workflows", href: listRoute.build({ fixture: route.fixture }) }, { label: route.workflowId, href: parentHref(route) }],
  }} />;

  const source = state.model;
  return (
    <main className="foundation-view workflows-view workflow-source" data-view="workflow-source" data-fixture={route.fixture || "live"}>
      <SourceNavigation route={route} />
      {state.status === "stale" && <RefreshStatus state={state} />}
      <header className="workflow-source__hero">
        <div><p className="eyebrow"><Code2 aria-hidden="true" /> Contained source</p><h1>{source.label || `${route.workflowId} source`}</h1><p>Read-only text associated with <strong>{route.workflowId}</strong>.</p></div>
        <span><LockKeyhole aria-hidden="true" /> Inert projection</span>
      </header>
      <section className="workflow-source__reader" aria-labelledby="workflow-source-reader-title">
        <header><div><p className="eyebrow">Closed metadata</p><h2 id="workflow-source-reader-title">Source contents</h2></div></header>
        <dl aria-label="Source metadata">
          <div><dt>Identity</dt><dd><code>{source.id}</code></dd></div>
          <div><dt>Language</dt><dd>{source.language}</dd></div>
          <div><dt>SHA-256</dt><dd><code>{source.sha256}</code></dd></div>
          <div><dt>Redaction</dt><dd>{source.redacted ? "Host details redacted" : "No redaction required"}</dd></div>
        </dl>
        <pre className="workflow-source__text" aria-label={`Source text for ${route.sourceId}`}><code>{source.text}</code></pre>
      </section>
      <p className="workflow-source__privacy"><LockKeyhole aria-hidden="true" /> This view renders text and closed metadata only. It never executes source content.</p>
    </main>
  );
}

export default WorkflowSourceView;
