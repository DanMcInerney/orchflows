import { BookOpen, Boxes, GitBranch, SearchX } from "lucide-react";

import type { FeatureState } from "../../../shared/transport/types";
import type { WorkflowCatalogItem, WorkflowCatalogModel } from "../model";
import type { WorkflowListRoute } from "../route";
import { detailRoute } from "../route";
import "../styles.css";
import { SummaryFlow } from "./SummaryFlow";

export interface WorkflowCatalogViewProps {
  route: WorkflowListRoute;
  state: FeatureState<WorkflowCatalogModel>;
}

function vocabularyLabel(workflow: WorkflowCatalogItem): string {
  return workflow.type === "composition" ? "T3 composition" : "T1 workflow skill";
}

function entryLabel(workflow: WorkflowCatalogItem): string {
  if (workflow.entry === "routed") return "Routed";
  if (workflow.entry === "named") return "Named";
  return "Callable";
}

function EmptyCatalog() {
  return (
    <section className="workflows-empty" aria-labelledby="workflows-empty-title">
      <SearchX aria-hidden="true" />
      <div>
        <h2 id="workflows-empty-title">No workflow definitions available</h2>
        <p>The canonical workflow catalog is empty. No run instances or invented definitions are shown.</p>
      </div>
    </section>
  );
}

export function WorkflowCatalogView({ route, state }: WorkflowCatalogViewProps) {
  if (!route.fixture && state.status === "loading") return <div className="loading">Waiting for reader</div>;
  if (!route.fixture && state.status === "error") return <div className="notice" role="status">{state.error.message}</div>;

  const workflows = state.model?.workflows ?? [];
  const compositions = workflows.filter((workflow) => workflow.type === "composition").length;
  const skills = workflows.length - compositions;

  return (
    <main className="foundation-view workflows-view" data-view="workflow-catalog" data-fixture={route.fixture || "live"}>
      {state.status === "stale" && <div className="notice" role="status">{state.error.message}</div>}
      <header className="workflows-hero">
        <div>
          <p className="eyebrow"><Boxes aria-hidden="true" /> Definition library</p>
          <h1>Workflows</h1>
          <p>What each workflow does, when to use it, and the shortest truthful path through it.</p>
        </div>
        <dl aria-label="Workflow catalog summary">
          <div><dt>Compositions</dt><dd>{compositions}</dd></div>
          <div><dt>Workflow skills</dt><dd>{skills}</dd></div>
        </dl>
      </header>

      {workflows.length === 0 ? <EmptyCatalog /> : (
        <section className="workflow-catalog" aria-labelledby="workflow-catalog-title">
          <header>
            <div>
              <p className="eyebrow"><BookOpen aria-hidden="true" /> Canonical definitions</p>
              <h2 id="workflow-catalog-title">Choose a workflow</h2>
            </div>
            <p><GitBranch aria-hidden="true" /> Summary flows are orientation, not run history.</p>
          </header>
          <ul className="workflow-catalog__list" aria-label="Workflow definitions">
            {workflows.map((workflow) => (
              <li key={workflow.id} className="workflow-catalog__row">
                <div className="workflow-catalog__identity">
                  <div className="workflow-catalog__meta">
                    <span>{vocabularyLabel(workflow)}</span>
                    <span>{entryLabel(workflow)}</span>
                  </div>
                  <h3>
                    <a href={detailRoute.build({ workflowId: workflow.id, fixture: route.fixture })}>{workflow.id}</a>
                  </h3>
                  <p>{workflow.description}</p>
                </div>
                <SummaryFlow workflowId={workflow.id} summary={workflow.summary} />
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}

export default WorkflowCatalogView;
