import { AlertTriangle, Bot, CheckCircle2, CircleDashed, Radio, Workflow } from "lucide-react";
import type { NodeProps } from "@xyflow/react";
import type { TopologyNode } from "./topology";

export interface SessionAgentNodeData extends Record<string, unknown>, TopologyNode {
  connection: string;
}

function StateGlyph({ state }: { state: string }) {
  if (state === "running") return <Radio aria-hidden="true" />;
  if (state === "finished" || state === "complete") return <CheckCircle2 aria-hidden="true" />;
  if (state === "attention" || state === "failed") return <AlertTriangle aria-hidden="true" />;
  return <CircleDashed aria-hidden="true" />;
}

export function SessionAgentNode({ data, selected }: NodeProps) {
  const node = data as SessionAgentNodeData;
  return (
    <article
      className="session-agent-node"
      data-kind={node.kind}
      data-state={node.state}
      data-selected={selected ? "true" : "false"}
    >
      <span className="session-agent-node__kind" aria-hidden="true">
        {node.kind === "session" ? <Workflow /> : <Bot />}
      </span>
      <div className="session-agent-node__identity">
        <strong>{node.label}</strong>
        <span>{node.type}</span>
      </div>
      <span className="session-agent-node__state">
        <StateGlyph state={node.state} /> {node.state}
      </span>
      <small>{node.connection}</small>
    </article>
  );
}
