import type { WorkflowSummary } from "../model";
import "../styles.css";

export type { SummaryEdge, SummaryNode, WorkflowSummary } from "../model";

const relationVerb = {
  sequence: "continues to",
  branch: "branches to",
  loop: "loops to",
} as const;

export interface SummaryFlowProps {
  workflowId: string;
  summary: WorkflowSummary;
  /** Optional exact state per node id; absent ids stay unstated rather than guessed. */
  nodeStates?: Record<string, string>;
}

export function SummaryFlow({ workflowId, summary, nodeStates }: SummaryFlowProps) {
  const labels = new Map(summary.nodes.map((node) => [node.id, node.label]));
  return (
    <figure className="workflow-summary" aria-label={`Summary flow for ${workflowId}`}>
      <div className="workflow-summary__visual" aria-hidden="true">
        <div className="workflow-summary__nodes" style={{ flexWrap: "wrap" }}>
          {summary.nodes.map((node, index) => (
            <span className="workflow-summary__node" data-state={nodeStates?.[node.id]} key={node.id}>
              {index > 0 && <i>→</i>}
              <b>{node.label}</b>
            </span>
          ))}
        </div>
        {summary.edges.some((edge) => edge.kind !== "sequence") && (
          <div className="workflow-summary__turns">
            {summary.edges.filter((edge) => edge.kind !== "sequence").map((edge, index) => (
              <span key={`${edge.source}-${edge.target}-${index}`} data-kind={edge.kind}>
                {edge.kind === "loop" ? "↻" : "↳"} {labels.get(edge.source)} → {labels.get(edge.target)}
              </span>
            ))}
          </div>
        )}
      </div>
      <ol className="sr-only" aria-label={`Nonvisual summary for ${workflowId}`}>
        {summary.nodes.map((node) => (
          <li key={`node-${node.id}`}>
            Step: {node.label}{nodeStates?.[node.id] ? `; ${nodeStates[node.id]}` : ""}
          </li>
        ))}
        {summary.edges.map((edge, index) => (
          <li key={`edge-${edge.source}-${edge.target}-${index}`}>
            {labels.get(edge.source)} {relationVerb[edge.kind]} {labels.get(edge.target)}
          </li>
        ))}
      </ol>
    </figure>
  );
}
