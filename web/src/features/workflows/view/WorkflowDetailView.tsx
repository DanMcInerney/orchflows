import { AlertTriangle, ArrowLeft, Braces, GitBranch, Link2, Network, SearchX } from "lucide-react";
import { useEffect, useState } from "react";

import type { FeatureState } from "../../../shared/transport/types";
import type { WorkflowDetailEdge, WorkflowDetailModel, WorkflowDetailNode } from "../model";
import type { WorkflowDetailRoute } from "../route";
import { listRoute, sourceRoute } from "../route";
import "../styles.css";
import { WorkflowGraph, type WorkflowSelection } from "./WorkflowGraph";

export interface WorkflowDetailViewProps {
  route: WorkflowDetailRoute;
  state: FeatureState<WorkflowDetailModel>;
}

function relationVerb(edge: WorkflowDetailEdge): string {
  if (edge.kind === "loop") return "loops to";
  if (edge.kind === "dependency") return "continues to";
  if (edge.kind === "executor") return "is executed by";
  return "calls";
}

function compactDetail(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia("(max-width: 1024px)").matches;
}

function sourceHref(route: WorkflowDetailRoute, sourceId: string): string {
  return sourceRoute.build({ workflowId: route.workflowId, sourceId, fixture: route.fixture });
}

function SourceLink({ node, route }: { node: WorkflowDetailNode; route: WorkflowDetailRoute }) {
  if (!node.sourceId) return <span className="workflow-source-missing">No resolved source</span>;
  return <a href={sourceHref(route, node.sourceId)}>View source for {node.label}</a>;
}

function Inspector({ route, selection }: { route: WorkflowDetailRoute; selection: WorkflowSelection }) {
  if (selection.type === "node") {
    const node = selection.value;
    return (
      <aside className="workflow-inspector" aria-labelledby="workflow-inspector-title">
        <header><p className="eyebrow"><Braces aria-hidden="true" /> Selected node</p><h2 id="workflow-inspector-title">{node.label}</h2></header>
        <dl>
          <div><dt>Kind</dt><dd>{node.kind}</dd></div>
          <div><dt>Identity</dt><dd><code>{node.id}</code></dd></div>
          <div><dt>Source</dt><dd><SourceLink node={node} route={route} /></dd></div>
        </dl>
        <p className="workflow-inspector__note">Exact projected metadata. Select any node or relation to inspect it.</p>
      </aside>
    );
  }

  const edge = selection.value;
  return (
    <aside className="workflow-inspector" aria-labelledby="workflow-inspector-title">
      <header><p className="eyebrow"><Link2 aria-hidden="true" /> Selected relation</p><h2 id="workflow-inspector-title">{edge.label}</h2></header>
      <dl>
        <div><dt>Kind</dt><dd>{edge.kind === "loop" ? "Loop relation" : edge.kind}</dd></div>
        <div><dt>From</dt><dd><code>{edge.from}</code></dd></div>
        <div><dt>To</dt><dd><code>{edge.to}</code></dd></div>
      </dl>
      <p className="workflow-inspector__note">This relation is projected from the canonical workflow definition.</p>
    </aside>
  );
}

function TopologyCompanion({ model, route }: { model: WorkflowDetailModel; route: WorkflowDetailRoute }) {
  const labels = new Map(model.nodes.map((node) => [node.id, node.label]));
  return (
    <section className="workflow-companion" role="region" aria-label="Complete ordered topology">
      <header><p className="eyebrow">Nonvisual equivalent</p><h3>Complete ordered topology</h3></header>
      <div>
        <section aria-labelledby="workflow-companion-nodes">
          <h4 id="workflow-companion-nodes">Nodes</h4>
          <ol aria-label="Workflow nodes">
            {model.nodes.map((node) => (
              <li key={node.id}>
                <span><b>{node.label}</b><small>{node.kind}</small></span>
                <SourceLink node={node} route={route} />
              </li>
            ))}
          </ol>
        </section>
        <section aria-labelledby="workflow-companion-relations">
          <h4 id="workflow-companion-relations">Relations</h4>
          <ol aria-label="Workflow relations">
            {model.relations.map((edge) => (
              <li key={edge.id} data-edge-id={edge.id} data-kind={edge.kind}>
                {labels.get(edge.from) ?? edge.from} {relationVerb(edge)} {labels.get(edge.to) ?? edge.to} — {edge.label}
              </li>
            ))}
          </ol>
        </section>
      </div>
    </section>
  );
}

function EmptyDetail({ route }: { route: WorkflowDetailRoute }) {
  return (
    <main className="foundation-view workflows-view workflow-detail" data-view="workflow-detail" data-fixture={route.fixture || "live"}>
      <nav className="workflow-breadcrumbs" aria-label="Breadcrumb">
        <a href={listRoute.build({ fixture: route.fixture })}>Workflows</a><span aria-hidden="true">/</span><span aria-current="page">{route.workflowId}</span>
      </nav>
      <section className="workflows-empty" aria-labelledby="workflow-empty-detail-title">
        <SearchX aria-hidden="true" />
        <div><h1 id="workflow-empty-detail-title">Topology is unavailable</h1><p>This definition has no exact nodes or relations to display.</p><a href={listRoute.build({ fixture: route.fixture })}><ArrowLeft aria-hidden="true" /> Back to Workflows</a></div>
      </section>
    </main>
  );
}

export function WorkflowDetailView({ route, state }: WorkflowDetailViewProps) {
  const [selectionKey, setSelectionKey] = useState(`node:${state.model?.nodes[0]?.id ?? ""}`);
  const [compact, setCompact] = useState(compactDetail);
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const query = window.matchMedia("(max-width: 1024px)");
    const changed = () => setCompact(query.matches);
    query.addEventListener("change", changed);
    changed();
    return () => query.removeEventListener("change", changed);
  }, []);
  if (!route.fixture && state.status === "loading") return <div className="loading">Waiting for reader</div>;
  if (!route.fixture && state.status === "error") return <div className="notice" role="status">{state.error.message}</div>;
  const model = state.model;
  if (!model || model.nodes.length === 0) return <EmptyDetail route={route} />;

  const selectedEdge = model.edges.find((item) => `edge:${item.id}` === selectionKey);
  const selectedNode = model.nodes.find((item) => `node:${item.id}` === selectionKey) ?? model.nodes[0];
  const selection: WorkflowSelection = selectedEdge
    ? { type: "edge", value: selectedEdge }
    : { type: "node", value: selectedNode };
  const select = (next: WorkflowSelection) => setSelectionKey(`${next.type}:${next.value.id}`);
  const inspector = <Inspector route={route} selection={selection} />;
  const graph = (
    <article className="workflow-detail__graph-panel">
      <header><div><p className="eyebrow"><GitBranch aria-hidden="true" /> Canonical topology</p><h2>Skills, scripts, work, and calls</h2></div><span>Observe only</span></header>
      <WorkflowGraph model={model} selection={selection} onSelect={select} />
      <TopologyCompanion model={model} route={route} />
    </article>
  );

  return (
    <main className="foundation-view workflows-view workflow-detail" data-view="workflow-detail" data-fixture={route.fixture || "live"}>
      {state.status === "stale" && <div className="notice" role="status">{state.error.message}</div>}
      <nav className="workflow-breadcrumbs" aria-label="Breadcrumb">
        <a href={listRoute.build({ fixture: route.fixture })}>Workflows</a><span aria-hidden="true">/</span><span aria-current="page">{model.id}</span>
      </nav>
      <header className="workflow-detail__hero">
        <div><p className="eyebrow"><Network aria-hidden="true" /> Exact definition · {model.tier}</p><h1>{model.id}</h1><p>{model.type === "composition" ? "Composition work, executors, dependencies, and loops." : "Workflow skill calls and invoked scripts."}</p></div>
        <dl aria-label="Topology summary"><div><dt>Nodes</dt><dd>{model.nodes.length}</dd></div><div><dt>Relations</dt><dd>{model.edges.length}</dd></div></dl>
      </header>

      {model.diagnostics.length > 0 && (
        <section className="workflow-diagnostics" aria-labelledby="workflow-diagnostic-title">
          <AlertTriangle aria-hidden="true" />
          <div>
            <h2 id="workflow-diagnostic-title">{model.diagnostics.length} topology {model.diagnostics.length === 1 ? "diagnostic" : "diagnostics"}</h2>
            <ul>{model.diagnostics.map((diagnostic) => <li key={`${diagnostic.code}:${diagnostic.subjectId}`}><b>{diagnostic.code}</b><span>{diagnostic.message}</span></li>)}</ul>
          </div>
        </section>
      )}

      <section className="workflow-detail__layout" aria-label="Workflow topology reader" data-layout={compact ? "compact" : "wide"}>
        {compact ? inspector : graph}
        {compact ? graph : inspector}
      </section>
    </main>
  );
}

export default WorkflowDetailView;
