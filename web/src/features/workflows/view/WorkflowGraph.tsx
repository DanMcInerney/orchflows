import { useEffect, useMemo, useRef } from "react";

import { layoutTopology } from "../../../layout";
import type { WorkflowDetailEdge, WorkflowDetailModel, WorkflowDetailNode } from "../model";

export type WorkflowSelection =
  | { type: "node"; value: WorkflowDetailNode }
  | { type: "edge"; value: WorkflowDetailEdge };

const STEP_STRIDE = 286;

function relationVerb(edge: WorkflowDetailEdge): string {
  if (edge.kind === "loop") return "loops to";
  if (edge.kind === "dependency") return "continues to";
  if (edge.kind === "executor") return "is executed by";
  if (edge.kind === "skill-call") return "calls skill";
  return "calls script";
}

function relationType(edge: WorkflowDetailEdge): string {
  if (edge.kind === "skill-call") return "skill call";
  if (edge.kind === "script-call") return "script call";
  return edge.kind;
}

function stableWorkOrder(model: WorkflowDetailModel): WorkflowDetailNode[] {
  const work = model.nodes.filter((node) => node.kind === "work");
  const identities = new Set(work.map((node) => node.id));
  const dependencies = model.edges.filter((edge) => (
    edge.kind === "dependency" && identities.has(edge.from) && identities.has(edge.to)
  ));
  const incoming = new Map(work.map((node) => [node.id, 0]));
  for (const edge of dependencies) incoming.set(edge.to, (incoming.get(edge.to) ?? 0) + 1);
  const pending = work.filter((node) => incoming.get(node.id) === 0);
  const ordered: WorkflowDetailNode[] = [];
  while (pending.length > 0) {
    const node = pending.shift();
    if (!node || ordered.some((item) => item.id === node.id)) continue;
    ordered.push(node);
    for (const edge of dependencies.filter((item) => item.from === node.id)) {
      const remaining = (incoming.get(edge.to) ?? 1) - 1;
      incoming.set(edge.to, remaining);
      if (remaining === 0) {
        const target = work.find((item) => item.id === edge.to);
        if (target) pending.push(target);
      }
    }
  }
  return [...ordered, ...work.filter((node) => !ordered.some((item) => item.id === node.id))];
}

function NodeButton({
  node,
  context,
  selection,
  onSelect,
}: {
  node: WorkflowDetailNode;
  context: string;
  selection: WorkflowSelection;
  onSelect(selection: WorkflowSelection): void;
}) {
  const selected = selection.type === "node" && selection.value.id === node.id;
  return (
    <button
      type="button"
      className="workflow-graph__node"
      data-kind={node.kind}
      data-node-id={node.id}
      aria-label={`Select ${context} ${node.label}`}
      aria-pressed={selected}
      onClick={() => onSelect({ type: "node", value: node })}
    >
      <span>{context}</span>
      <strong>{node.label}</strong>
    </button>
  );
}

function RelationControl({
  edge,
  labels,
  selection,
  onSelect,
  compact = false,
}: {
  edge: WorkflowDetailEdge;
  labels: Map<string, string>;
  selection: WorkflowSelection;
  onSelect(selection: WorkflowSelection): void;
  compact?: boolean;
}) {
  const from = labels.get(edge.from) ?? edge.from;
  const to = labels.get(edge.to) ?? edge.to;
  return (
    <div className="workflow-graph__relation" data-kind={edge.kind} data-compact={compact ? "true" : "false"}>
      <span
        className="workflow-graph__connector"
        data-workflow-connector={edge.id}
        data-edge-kind={edge.kind}
        data-self-loop={edge.from === edge.to ? "true" : "false"}
        aria-hidden="true"
      />
      <button
        type="button"
        className="workflow-graph__edge"
        data-kind={edge.kind}
        aria-label={`Select ${relationType(edge)} relation: ${from} ${relationVerb(edge)} ${to}`}
        aria-pressed={selection.type === "edge" && selection.value.id === edge.id}
        onClick={() => onSelect({ type: "edge", value: edge })}
      >
        <span aria-hidden="true">{edge.kind === "loop" ? "↻" : "→"}</span>
        {edge.label || relationType(edge)}
      </button>
    </div>
  );
}

function CompositionFlow({ model, selection, onSelect }: WorkflowGraphProps) {
  const labels = new Map(model.nodes.map((node) => [node.id, node.label]));
  const nodes = new Map(model.nodes.map((node) => [node.id, node]));
  const steps = stableWorkOrder(model);
  const executorEdges = model.edges.filter((edge) => edge.kind === "executor");
  const dependencyEdges = model.edges.filter((edge) => edge.kind === "dependency");
  const loopEdges = model.edges.filter((edge) => edge.kind === "loop");
  const presentedNodeIds = new Set(steps.map((node) => node.id));
  for (const edge of executorEdges) presentedNodeIds.add(edge.to);
  const remainingNodes = model.nodes.filter((node) => !presentedNodeIds.has(node.id));
  const presentedEdgeIds = new Set([...executorEdges, ...dependencyEdges, ...loopEdges].map((edge) => edge.id));
  const remainingEdges = model.edges.filter((edge) => !presentedEdgeIds.has(edge.id));

  return (
    <div className="workflow-step-flow" data-flow-kind="composition">
      <ol className="workflow-step-flow__sequence" aria-label="Workflow skill sequence">
        {steps.map((work, index) => {
          const executors = executorEdges.filter((edge) => edge.from === work.id);
          const loops = loopEdges.filter((edge) => edge.from === work.id);
          const outgoing = dependencyEdges.filter((edge) => edge.from === work.id);
          return (
            <li className="workflow-step-flow__item" key={work.id} data-step-id={work.id}>
              <article className="workflow-step-card">
                <header>
                  <span>Step {index + 1}</span>
                  <small>{outgoing.length > 1 ? `${outgoing.length} branches` : "In sequence"}</small>
                </header>
                <div className="workflow-step-card__primary">
                  {executors.map((edge) => {
                    const executor = nodes.get(edge.to);
                    return executor ? (
                      <NodeButton
                        key={`${work.id}:${edge.id}`}
                        node={executor}
                        context="Called skill"
                        selection={selection}
                        onSelect={onSelect}
                      />
                    ) : (
                      <p className="workflow-step-card__unresolved" key={edge.id}>Unresolved executor</p>
                    );
                  })}
                  {executors.length === 0 && <p className="workflow-step-card__unresolved">No resolved executor</p>}
                </div>
                <div className="workflow-step-card__coupling">
                  {executors.map((edge) => (
                    <RelationControl key={edge.id} edge={edge} labels={labels} selection={selection} onSelect={onSelect} compact />
                  ))}
                  <NodeButton
                    node={work}
                    context="Definition-time ticket template"
                    selection={selection}
                    onSelect={onSelect}
                  />
                  <p>Reusable work definition. A runtime ticket is created only when this composition is instantiated.</p>
                </div>
                {loops.map((edge) => (
                  <div className="workflow-step-card__loop" key={edge.id}>
                    <RelationControl edge={edge} labels={labels} selection={selection} onSelect={onSelect} compact />
                  </div>
                ))}
              </article>
              {outgoing.length > 0 && (
                <div className="workflow-step-flow__handoff" aria-label={`Relations after step ${index + 1}`}>
                  {outgoing.map((edge) => (
                    <RelationControl key={edge.id} edge={edge} labels={labels} selection={selection} onSelect={onSelect} />
                  ))}
                </div>
              )}
            </li>
          );
        })}
      </ol>
      {(remainingNodes.length > 0 || remainingEdges.length > 0) && (
        <section className="workflow-step-flow__additional" aria-labelledby="workflow-additional-calls">
          <h3 id="workflow-additional-calls">Additional canonical calls</h3>
          <div>
            {remainingNodes.map((node) => (
              <NodeButton key={node.id} node={node} context={`${node.kind} definition`} selection={selection} onSelect={onSelect} />
            ))}
            {remainingEdges.map((edge) => (
              <RelationControl key={edge.id} edge={edge} labels={labels} selection={selection} onSelect={onSelect} compact />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function CallableFlow({ model, selection, onSelect }: WorkflowGraphProps) {
  const labels = new Map(model.nodes.map((node) => [node.id, node.label]));
  const nodes = new Map(model.nodes.map((node) => [node.id, node]));
  const caller = model.nodes.find((node) => node.kind === "workflow") ?? model.nodes[0];
  const calls = model.edges.filter((edge) => edge.kind === "skill-call" || edge.kind === "script-call");
  const calledIds = new Set(calls.map((edge) => edge.to));
  const remainingNodes = model.nodes.filter((node) => node.id !== caller?.id && !calledIds.has(node.id));
  const remainingEdges = model.edges.filter((edge) => !calls.some((call) => call.id === edge.id));

  return (
    <div className="workflow-step-flow" data-flow-kind="callable">
      {caller && (
        <div className="workflow-callable-origin">
          <NodeButton node={caller} context="Workflow definition" selection={selection} onSelect={onSelect} />
          <p>This callable workflow invokes the skills and scripts below in canonical relation order.</p>
        </div>
      )}
      <ol className="workflow-step-flow__sequence" aria-label="Called skills and scripts">
        {calls.map((edge, index) => {
          const target = nodes.get(edge.to);
          return (
            <li className="workflow-step-flow__item" key={edge.id}>
              <div className="workflow-step-flow__handoff workflow-step-flow__handoff--call">
                <RelationControl edge={edge} labels={labels} selection={selection} onSelect={onSelect} />
              </div>
              <article className="workflow-step-card workflow-step-card--call">
                <header><span>Call {index + 1}</span><small>{edge.kind === "skill-call" ? "Skill" : "Script"}</small></header>
                {target ? (
                  <NodeButton
                    node={target}
                    context={target.kind === "script" ? "Called script" : "Called skill"}
                    selection={selection}
                    onSelect={onSelect}
                  />
                ) : <p className="workflow-step-card__unresolved">Unresolved call target</p>}
              </article>
            </li>
          );
        })}
      </ol>
      {(remainingNodes.length > 0 || remainingEdges.length > 0) && (
        <section className="workflow-step-flow__additional" aria-labelledby="workflow-additional-relations">
          <h3 id="workflow-additional-relations">Additional canonical relations</h3>
          <div>
            {remainingNodes.map((node) => (
              <NodeButton key={node.id} node={node} context={`${node.kind} definition`} selection={selection} onSelect={onSelect} />
            ))}
            {remainingEdges.map((edge) => (
              <RelationControl key={edge.id} edge={edge} labels={labels} selection={selection} onSelect={onSelect} compact />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

export interface WorkflowGraphProps {
  model: WorkflowDetailModel;
  selection: WorkflowSelection;
  onSelect(selection: WorkflowSelection): void;
}

export function WorkflowGraph({ model, selection, onSelect }: WorkflowGraphProps) {
  const graphRef = useRef<HTMLDivElement>(null);
  const workOrder = useMemo(() => stableWorkOrder(model), [model]);
  const topology = useMemo(() => ({
    nodes: model.nodes.map((node) => ({ id: node.id })),
    edges: model.edges.map((edge) => ({ id: edge.id, source: edge.from, target: edge.to })),
    direction: "RIGHT" as const,
  }), [model.edges, model.nodes]);

  useEffect(() => {
    if (typeof Worker === "undefined") return;
    void layoutTopology(topology).catch(() => undefined);
  }, [topology]);

  useEffect(() => {
    const graph = graphRef.current;
    if (!graph || graph.clientWidth <= 0) return;
    const selectedId = selection.type === "node" ? selection.value.id : selection.value.from;
    const direct = workOrder.findIndex((node) => node.id === selectedId);
    const executor = model.edges.find((edge) => edge.kind === "executor" && edge.to === selectedId);
    const index = direct >= 0 ? direct : workOrder.findIndex((node) => node.id === executor?.from);
    if (index >= 0) graph.scrollLeft = Math.max(0, index * STEP_STRIDE - graph.clientWidth / 2);
  }, [model.edges, selection, workOrder]);

  return (
    <div ref={graphRef} className="workflow-graph" role="group" aria-label={`Exact topology for ${model.id}`}>
      {model.type === "composition"
        ? <CompositionFlow model={model} selection={selection} onSelect={onSelect} />
        : <CallableFlow model={model} selection={selection} onSelect={onSelect} />}
    </div>
  );
}
