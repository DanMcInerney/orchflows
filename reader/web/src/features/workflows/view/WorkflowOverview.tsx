import { useState } from "react";
import type { WorkflowDetailModel } from "../model";
import type { WorkflowDetailRoute } from "../route";
import { sourceRoute } from "../route";

export function WorkflowOverview({ model, route }: {
  model: WorkflowDetailModel;
  route: WorkflowDetailRoute;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const summary = model.summary;
  const definition = model.nodes.find((node) => node.kind === "workflow");
  const labels = new Map(summary?.nodes.map((node) => [node.id, node.label]));
  const step = summary?.nodes.find((node) => node.id === selected);
  const exact = model.nodes.find((node) => node.id === selected);
  return <section className="workflow-overview" aria-labelledby="workflow-overview-title">
    <h2 id="workflow-overview-title">Overview</h2>
    {model.description && <p>{model.description}</p>}
    {summary ? <>
      <ol className="workflow-overview__steps" aria-label="Semantic workflow steps">
        {summary.nodes.map((node, index) => <li key={node.id}>
          <button type="button" aria-pressed={selected === node.id} aria-controls="workflow-overview-selection"
            onClick={() => setSelected(node.id)}><span>{index + 1}</span><strong>{node.label}</strong></button>
        </li>)}
      </ol>
      <div className="workflow-overview__loops">
        {summary.edges.filter((edge) => edge.kind !== "sequence").map((edge, index) => {
          const relation = model.edges.find((item) => item.kind === edge.kind && item.from === edge.source && item.to === edge.target);
          return <p key={index}>{edge.kind === "loop" ? "↻ Loop" : "↳ Branch"}: {labels.get(edge.source)} → {labels.get(edge.target)}
            {relation?.label && <span> · {relation.label}</span>}
          </p>;
        })}
      </div>
      <div id="workflow-overview-selection" className="workflow-overview__selection" aria-live="polite">
        {step ? <><h3>{step.label}</h3>
          <p>{summary.edges.filter((edge) => edge.source === step.id).map((edge) =>
            `${edge.kind === "loop" ? "Loops to" : edge.kind === "branch" ? "Branches to" : "Continues to"} ${labels.get(edge.target)}`).join(". ") || "Final phase in this summary."}</p>
          {exact && <aside aria-label={exact.label} aria-live="polite" className="workflow-overview__template">
            <p>Ticket template: <strong>{exact.label}</strong></p>
            {exact.sourceId && <a href={sourceRoute.build({ workflowId: route.workflowId, sourceId: exact.sourceId, fixture: route.fixture })}>View source for {exact.label}</a>}
          </aside>}
          {!exact && <p>This semantic phase has no separately projected ticket template. Read the workflow source for its conditions and instructions.</p>}
          <button type="button" className="workflow-overview__close" onClick={() => setSelected(null)}>Close selected details</button>
        </> : <p>Select a phase to see its place in the workflow.</p>}
      </div>
    </> : <p>A semantic summary is unavailable for this definition. Source references below do not establish execution order or loops.</p>}
    {definition?.sourceId && <a href={sourceRoute.build({ workflowId: route.workflowId, sourceId: definition.sourceId, fixture: route.fixture })}>Read {definition.label} workflow source</a>}
  </section>;
}
