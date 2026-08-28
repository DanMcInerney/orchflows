import { AlertTriangle, ArrowLeft, Braces, GitBranch, Link2, Network, SearchX } from "lucide-react";
import { useState } from "react";

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

function sourceHref(route: WorkflowDetailRoute, sourceId: string): string {
  return sourceRoute.build({ workflowId: route.workflowId, sourceId, fixture: route.fixture });
}

function SourceLink({ node, route }: { node: WorkflowDetailNode; route: WorkflowDetailRoute }) {
  if (!node.sourceId) return <span className="workflow-source-missing">No resolved source</span>;
  return <a href={sourceHref(route, node.sourceId)}>View source for {node.label}</a>;
}

function nodeKindLabel(node: WorkflowDetailNode): string {
  if (node.kind === "work") return "Definition-time ticket template";
  if (node.kind === "workflow") return "Workflow definition";
  if (node.kind === "skill") return "Skill definition";
  return "Script definition";
}

function Inspector({ route, selection }: { route: WorkflowDetailRoute; selection: WorkflowSelection }) {
  if (selection.type === "node") {
    const node = selection.value;
    return (
      <aside
        id="workflow-inspector"
        className="workflow-inspector"
        aria-labelledby="workflow-inspector-title"
        aria-live="polite"
        aria-atomic="true"
      >
        <header><p className="eyebrow"><Braces aria-hidden="true" /> Selected node</p><h2 id="workflow-inspector-title">{node.label}</h2></header>
        <dl>
          <div><dt>Kind</dt><dd>{nodeKindLabel(node)}</dd></div>
          <div><dt>Identity</dt><dd><code>{node.id}</code></dd></div>
          <div><dt>Source</dt><dd><SourceLink node={node} route={route} /></dd></div>
        </dl>
        <p className="workflow-inspector__note">{node.kind === "work"
          ? "Exact projected metadata. Ticket templates define future work; they are not runtime tickets."
          : "Exact projected metadata for this canonical definition."}</p>
      </aside>
    );
  }

  const edge = selection.value;
  return (
    <aside
      id="workflow-inspector"
      className="workflow-inspector"
      aria-labelledby="workflow-inspector-title"
      aria-live="polite"
      aria-atomic="true"
    >
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
  const work = model.nodes.filter((node) => node.kind === "work");
  const calls = model.edges.filter((edge) => edge.kind === "skill-call" || edge.kind === "script-call");
  return (
    <section className="workflow-companion" role="region" aria-label="Complete ordered topology">
      <header><p className="eyebrow">Nonvisual equivalent</p><h3>Complete ordered topology</h3></header>
      <section className="workflow-companion__sequence" aria-labelledby="workflow-companion-sequence">
        <h4 id="workflow-companion-sequence">{model.type === "composition" ? "Step sequence" : "Call sequence"}</h4>
        {model.type === "composition" ? (
          <ol aria-label="Workflow steps">
            {work.map((template, index) => {
              const executors = model.edges
                .filter((edge) => edge.kind === "executor" && edge.from === template.id)
                .map((edge) => labels.get(edge.to) ?? edge.to);
              const loops = model.edges.filter((edge) => edge.kind === "loop" && edge.from === template.id);
              return (
                <li key={template.id}>
                  <b>Step {index + 1}: {executors.join(", ") || "Unresolved executor"}</b>
                  <span>Called skill for definition-time ticket template <code>{template.label}</code>.</span>
                  {loops.map((edge) => <small key={edge.id}>Repeats: {edge.label}.</small>)}
                </li>
              );
            })}
          </ol>
        ) : (
          <ol aria-label="Workflow calls">
            {calls.map((edge, index) => (
              <li key={edge.id}>
                <b>Call {index + 1}: {labels.get(edge.to) ?? edge.to}</b>
                <span>{edge.kind === "skill-call" ? "Called skill" : "Called script"} from {labels.get(edge.from) ?? edge.from}.</span>
              </li>
            ))}
          </ol>
        )}
      </section>
      <div>
        <section aria-labelledby="workflow-companion-nodes">
          <h4 id="workflow-companion-nodes">Nodes</h4>
          <ol aria-label="Workflow nodes">
            {model.nodes.map((node) => (
              <li key={node.id}>
                <span><b>{node.label}</b><small>{nodeKindLabel(node)}</small></span>
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
  const firstNode = state.model?.nodes[0];
  const firstOccurrence = firstNode?.kind === "workflow"
    ? `node:${firstNode.id}:definition`
    : `node:${firstNode?.id ?? ""}:model`;
  const [selectionKey, setSelectionKey] = useState<{
    type: "node" | "edge";
    id: string;
    occurrenceId: string;
  }>({
    type: "node",
    id: firstNode?.id ?? "",
    occurrenceId: firstOccurrence,
  });
  if (!route.fixture && state.status === "loading") return <div className="loading">Waiting for reader</div>;
  if (!route.fixture && state.status === "error") return <div className="notice" role="status">{state.error.message}</div>;
  const model = state.model;
  if (!model || model.nodes.length === 0) return <EmptyDetail route={route} />;

  const selectedEdge = selectionKey.type === "edge"
    ? model.edges.find((item) => item.id === selectionKey.id)
    : undefined;
  const selectedNode = selectionKey.type === "node"
    ? model.nodes.find((item) => item.id === selectionKey.id) ?? model.nodes[0]
    : model.nodes[0];
  const selection: WorkflowSelection = selectedEdge
    ? { type: "edge", value: selectedEdge, occurrenceId: selectionKey.occurrenceId }
    : { type: "node", value: selectedNode, occurrenceId: selectionKey.occurrenceId };
  const select = (next: WorkflowSelection) => setSelectionKey({
    type: next.type,
    id: next.value.id,
    occurrenceId: next.occurrenceId,
  });
  const inspector = <Inspector route={route} selection={selection} />;
  const graph = (
    <article className="workflow-detail__graph-panel">
      <header>
        <div>
          <p className="eyebrow"><GitBranch aria-hidden="true" /> {model.type === "composition" ? "Composition flow" : "Callable workflow"}</p>
          <h2>{model.type === "composition" ? "Skills called, step by step" : "Skills and scripts called"}</h2>
          <p>{model.type === "composition"
            ? "Each skill is paired with the reusable ticket template that defines its work. Runtime tickets are created later."
            : "The workflow definition calls each skill or script below; relation order remains canonical."}</p>
        </div>
        <span>Observe only</span>
      </header>
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
        <div><p className="eyebrow"><Network aria-hidden="true" /> Exact definition · {model.tier}</p><h1>{model.id}</h1><p>{model.type === "composition" ? "A reusable composition shown as the ordered skills it calls." : "A callable workflow shown as its ordered skill and script calls."}</p></div>
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

      <section className="workflow-detail__layout" aria-label="Workflow topology reader">
        {graph}
        {inspector}
      </section>
    </main>
  );
}

export default WorkflowDetailView;
