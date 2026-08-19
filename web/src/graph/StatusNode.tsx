import { Handle, Position, type NodeProps } from "@xyflow/react";

export interface StatusNodeData extends Record<string, unknown> {
  label: string;
  status: string;
  explanation: string;
}

export function StatusNode({ data, selected }: NodeProps) {
  const node = data as StatusNodeData;
  return (
    <article className="status-node" data-status={node.status} aria-current={selected ? "true" : undefined}>
      <Handle type="target" position={Position.Left} isConnectable={false} aria-hidden="true" />
      <span className="status-node__glyph" aria-hidden="true">●</span>
      <strong>{node.label}</strong>
      <span className="status-node__status">{node.status}</span>
      <small>{node.explanation}</small>
      <Handle type="source" position={Position.Right} isConnectable={false} aria-hidden="true" />
    </article>
  );
}
