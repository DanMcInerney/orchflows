import { ArrowLeft, Code2, FileQuestion, FileWarning, LockKeyhole } from "lucide-react";

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
      <nav className="workflow-breadcrumbs" aria-label="Breadcrumb">
        <a href={listRoute.build({ fixture: route.fixture })}>Workflows</a>
        <span aria-hidden="true">/</span>
        <a href={parentHref(route)}>{route.workflowId}</a>
        <span aria-hidden="true">/</span>
        <span aria-current="page">{route.sourceId}</span>
      </nav>
      <a className="workflow-source__back" href={parentHref(route)}><ArrowLeft aria-hidden="true" /> Back to {route.workflowId}</a>
    </>
  );
}

function ClosedSourceState({ route, kind }: { route: WorkflowSourceRoute; kind: "loading" | "missing" | "unreadable" | "unavailable" }) {
  const content = {
    loading: ["Waiting for source", "The reader is preparing a safe, contained source projection."],
    missing: ["Source not found", "This opaque source identity is not associated with this workflow."],
    unreadable: ["Source is unreadable", "Safe source metadata could not be projected for this cataloged identity."],
    unavailable: ["Source is unavailable", "The source reader is temporarily unavailable. No file details were exposed."],
  } as const;
  const [title, message] = content[kind];
  return (
    <main className="foundation-view workflows-view workflow-source" data-view="workflow-source" data-fixture={route.fixture || "live"}>
      <SourceNavigation route={route} />
      <section className="workflow-source__state" aria-labelledby="workflow-source-state-title">
        {kind === "missing" ? <FileQuestion aria-hidden="true" /> : <FileWarning aria-hidden="true" />}
        <div><h1 id="workflow-source-state-title">{title}</h1><p>{message}</p></div>
      </section>
    </main>
  );
}

export function WorkflowSourceView({ route, state }: WorkflowSourceViewProps) {
  if (state.status === "loading") return <ClosedSourceState route={route} kind="loading" />;
  if (state.status === "error") {
    const kind = state.error.code === "not-found" ? "missing" : state.error.code === "invalid-payload" ? "unreadable" : "unavailable";
    return <ClosedSourceState route={route} kind={kind} />;
  }

  const source = state.model;
  return (
    <main className="foundation-view workflows-view workflow-source" data-view="workflow-source" data-fixture={route.fixture || "live"}>
      <SourceNavigation route={route} />
      {state.status === "stale" && <div className="notice" role="status">Source refresh failed. Showing the last safe projection.</div>}
      <header className="workflow-source__hero">
        <div><p className="eyebrow"><Code2 aria-hidden="true" /> Contained source</p><h1>{route.sourceId}</h1><p>Read-only text associated with <strong>{route.workflowId}</strong>.</p></div>
        <span><LockKeyhole aria-hidden="true" /> Inert projection</span>
      </header>
      <section className="workflow-source__reader" aria-labelledby="workflow-source-reader-title">
        <header><div><p className="eyebrow">Closed metadata</p><h2 id="workflow-source-reader-title">Source contents</h2></div></header>
        <dl aria-label="Source metadata">
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
