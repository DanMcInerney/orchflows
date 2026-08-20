import { useEffect, useMemo, useRef, useState } from "react";

import { layoutTopology } from "../../../layout";
import type { WorkflowDetailEdge, WorkflowDetailModel, WorkflowDetailNode } from "../model";

export type WorkflowSelection =
  | { type: "node"; value: WorkflowDetailNode }
  | { type: "edge"; value: WorkflowDetailEdge };

interface Point {
  x: number;
  y: number;
}

interface ConnectorGeometry {
  path: string;
  label: Point;
  selfLoop: boolean;
}

const NODE_WIDTH = 184;
const NODE_HEIGHT = 78;
const COLUMN_GAP = 76;
const ROW_GAP = 106;
const CANVAS_GUTTER = 42;

const kindRow: Record<WorkflowDetailNode["kind"], number> = {
  workflow: 0,
  work: 0,
  skill: 1,
  script: 2,
};

function fallbackPositions(nodes: WorkflowDetailNode[]): Record<string, Point> {
  const rowCounts = new Map<number, number>();
  return Object.fromEntries(nodes.map((node) => {
    const row = kindRow[node.kind];
    const column = rowCounts.get(row) ?? 0;
    rowCounts.set(row, column + 1);
    return [node.id, {
      x: CANVAS_GUTTER + column * (NODE_WIDTH + COLUMN_GAP),
      y: CANVAS_GUTTER + 58 + row * (NODE_HEIGHT + ROW_GAP),
    }];
  }));
}

function normalizePositions(nodes: WorkflowDetailNode[], positions: Record<string, Point>): Record<string, Point> {
  const available = nodes.map((node) => positions[node.id]).filter((point): point is Point => Boolean(point));
  if (available.length !== nodes.length) return fallbackPositions(nodes);
  const minimumX = Math.min(...available.map((point) => point.x));
  const minimumY = Math.min(...available.map((point) => point.y));
  return Object.fromEntries(nodes.map((node) => [node.id, {
    x: positions[node.id].x - minimumX + CANVAS_GUTTER,
    y: positions[node.id].y - minimumY + CANVAS_GUTTER + 58,
  }]));
}

function connectorGeometry(edge: WorkflowDetailEdge, positions: Record<string, Point>): ConnectorGeometry | null {
  const source = positions[edge.from];
  const target = positions[edge.to];
  if (!source || !target) return null;

  if (edge.from === edge.to) {
    const startX = source.x + NODE_WIDTH * .72;
    const endX = source.x + NODE_WIDTH * .28;
    const y = source.y;
    return {
      path: `M ${startX} ${y} C ${startX + 72} ${y - 72}, ${endX - 72} ${y - 72}, ${endX} ${y}`,
      label: { x: source.x + NODE_WIDTH / 2, y: y - 66 },
      selfLoop: true,
    };
  }

  const leftToRight = target.x >= source.x;
  const vertical = Math.abs(target.y - source.y) > Math.abs(target.x - source.x);
  if (vertical) {
    const topToBottom = target.y >= source.y;
    const sourceX = source.x + NODE_WIDTH / 2;
    const targetX = target.x + NODE_WIDTH / 2;
    const sourceY = source.y + (topToBottom ? NODE_HEIGHT : 0);
    const targetY = target.y + (topToBottom ? 0 : NODE_HEIGHT);
    const bend = Math.max(54, Math.abs(targetY - sourceY) * .42);
    const direction = topToBottom ? 1 : -1;
    return {
      path: `M ${sourceX} ${sourceY} C ${sourceX} ${sourceY + bend * direction}, ${targetX} ${targetY - bend * direction}, ${targetX} ${targetY}`,
      label: { x: (sourceX + targetX) / 2, y: (sourceY + targetY) / 2 },
      selfLoop: false,
    };
  }

  const sourceX = source.x + (leftToRight ? NODE_WIDTH : 0);
  const targetX = target.x + (leftToRight ? 0 : NODE_WIDTH);
  const sourceY = source.y + NODE_HEIGHT / 2;
  const targetY = target.y + NODE_HEIGHT / 2;
  const bend = Math.max(54, Math.abs(targetX - sourceX) * .42);
  const direction = leftToRight ? 1 : -1;
  return {
    path: `M ${sourceX} ${sourceY} C ${sourceX + bend * direction} ${sourceY}, ${targetX - bend * direction} ${targetY}, ${targetX} ${targetY}`,
    label: { x: (sourceX + targetX) / 2, y: (sourceY + targetY) / 2 },
    selfLoop: false,
  };
}

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

export interface WorkflowGraphProps {
  model: WorkflowDetailModel;
  selection: WorkflowSelection;
  onSelect(selection: WorkflowSelection): void;
}

export function WorkflowGraph({ model, selection, onSelect }: WorkflowGraphProps) {
  const graphRef = useRef<HTMLDivElement>(null);
  const [positions, setPositions] = useState(() => fallbackPositions(model.nodes));
  const topology = useMemo(() => ({
    nodes: model.nodes.map(({ id }) => ({ id })),
    edges: model.edges.map((edge) => ({ id: edge.id, source: edge.from, target: edge.to })),
    direction: "DOWN" as const,
  }), [model.edges, model.nodes]);

  useEffect(() => {
    let current = true;
    setPositions(fallbackPositions(model.nodes));
    if (typeof Worker === "undefined") return () => { current = false; };
    void layoutTopology(topology).then((next) => {
      if (current) setPositions(normalizePositions(model.nodes, next));
    }).catch(() => undefined);
    return () => { current = false; };
  }, [model.nodes, topology]);

  const labels = new Map(model.nodes.map((node) => [node.id, node.label]));
  const connectors = model.edges.map((edge) => ({ edge, geometry: connectorGeometry(edge, positions) }));
  useEffect(() => {
    const graph = graphRef.current;
    if (!graph || graph.clientWidth <= 0) return;
    const selectedPoint = selection.type === "node"
      ? positions[selection.value.id] && {
          x: positions[selection.value.id].x + NODE_WIDTH / 2,
          y: positions[selection.value.id].y + NODE_HEIGHT / 2,
        }
      : connectorGeometry(selection.value, positions)?.label;
    if (!selectedPoint) return;
    graph.scrollLeft = Math.max(0, selectedPoint.x - graph.clientWidth / 2);
  }, [positions, selection]);
  const width = Math.max(680, ...Object.values(positions).map((point) => point.x + NODE_WIDTH + CANVAS_GUTTER));
  const height = Math.max(360, ...Object.values(positions).map((point) => point.y + NODE_HEIGHT + CANVAS_GUTTER));

  return (
    <div ref={graphRef} className="workflow-graph" role="group" aria-label={`Exact topology for ${model.id}`}>
      <div className="workflow-graph__canvas" style={{ width, height }}>
        <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height} aria-hidden="true">
          <defs>
            <marker id="workflow-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" />
            </marker>
          </defs>
          {connectors.map(({ edge, geometry }) => geometry && (
            <path
              key={edge.id}
              className="workflow-graph__connector"
              data-workflow-connector={edge.id}
              data-edge-kind={edge.kind}
              data-self-loop={geometry.selfLoop ? "true" : "false"}
              d={geometry.path}
              markerEnd="url(#workflow-arrow)"
            />
          ))}
        </svg>

        {model.nodes.map((node) => {
          const point = positions[node.id];
          return point && (
            <button
              key={node.id}
              type="button"
              className="workflow-graph__node"
              data-kind={node.kind}
              aria-label={`Select ${node.kind} ${node.label}`}
              aria-pressed={selection.type === "node" && selection.value.id === node.id}
              style={{ left: point.x, top: point.y, width: NODE_WIDTH, height: NODE_HEIGHT }}
              onClick={() => onSelect({ type: "node", value: node })}
            >
              <span>{node.kind}</span>
              <strong>{node.label}</strong>
            </button>
          );
        })}

        {connectors.map(({ edge, geometry }) => {
          if (!geometry) return null;
          const from = labels.get(edge.from) ?? edge.from;
          const to = labels.get(edge.to) ?? edge.to;
          return (
            <button
              key={`label:${edge.id}`}
              type="button"
              className="workflow-graph__edge"
              data-kind={edge.kind}
              aria-label={`Select ${edge.kind} ${from} ${relationVerb(edge)} ${to}`}
              aria-pressed={selection.type === "edge" && selection.value.id === edge.id}
              style={{ left: geometry.label.x, top: geometry.label.y }}
              onClick={() => onSelect({ type: "edge", value: edge })}
            >
              <span aria-hidden="true">{edge.kind === "loop" ? "↻" : "→"}</span>
              {relationType(edge)}
            </button>
          );
        })}
      </div>
    </div>
  );
}
