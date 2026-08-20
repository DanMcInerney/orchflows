import { ArrowRight, GitBranch, RotateCcw } from "lucide-react";

import type { WorkflowDetailEdge, WorkflowDetailModel, WorkflowDetailNode } from "../model";

export type WorkflowSelection =
  | { type: "node"; value: WorkflowDetailNode }
  | { type: "edge"; value: WorkflowDetailEdge };

function relationVerb(edge: WorkflowDetailEdge): string {
  if (edge.kind === "loop") return "loops to";
  if (edge.kind === "dependency") return "continues to";
  return "connects to";
}

export interface WorkflowGraphProps {
  model: WorkflowDetailModel;
  selection: WorkflowSelection;
  onSelect(selection: WorkflowSelection): void;
}

export function WorkflowGraph({ model, selection, onSelect }: WorkflowGraphProps) {
  const labels = new Map(model.nodes.map((node) => [node.id, node.label]));
  return (
    <div className="workflow-graph" role="group" aria-label={`Exact topology for ${model.id}`}>
      <ol className="workflow-graph__nodes" aria-label="Selectable graph nodes">
        {model.nodes.map((node) => (
          <li key={node.id}>
            <button
              type="button"
              className="workflow-graph__node"
              data-kind={node.kind}
              aria-label={`Select ${node.kind} ${node.label}`}
              aria-pressed={selection.type === "node" && selection.value.id === node.id}
              onClick={() => onSelect({ type: "node", value: node })}
            >
              <span>{node.kind}</span>
              <strong>{node.label}</strong>
            </button>
          </li>
        ))}
      </ol>
      <ol className="workflow-graph__edges" aria-label="Selectable graph relations">
        {model.edges.map((edge) => {
          const from = labels.get(edge.from) ?? edge.from;
          const to = labels.get(edge.to) ?? edge.to;
          const verb = relationVerb(edge);
          return (
            <li key={edge.id}>
              <button
                type="button"
                className="workflow-graph__edge"
                data-kind={edge.kind}
                aria-label={`Select ${edge.kind} ${from} ${verb} ${to}`}
                aria-pressed={selection.type === "edge" && selection.value.id === edge.id}
                onClick={() => onSelect({ type: "edge", value: edge })}
              >
                {edge.kind === "loop" ? <RotateCcw aria-hidden="true" /> : edge.kind === "dependency" ? <ArrowRight aria-hidden="true" /> : <GitBranch aria-hidden="true" />}
                <span><strong>{from}</strong><small>{edge.label}</small><strong>{to}</strong></span>
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
