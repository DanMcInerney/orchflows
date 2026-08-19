import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import type { TicketSummary } from "../api/schema";
import { RunGraph } from "./RunGraph";

vi.mock("@xyflow/react", () => ({
  ReactFlowProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  ReactFlow: ({ children, nodes, edges, nodeTypes, ...props }: any) => {
    const NodeComponent = nodeTypes.status;
    return <div aria-label={props["aria-label"]}>
      {nodes.map((node: any) => <NodeComponent key={node.id} data={node.data} selected={false} />)}
      {edges.map((edge: any) => <span key={edge.id} aria-label={edge.ariaLabel} />)}
      {children}
    </div>;
  },
  Background: () => null,
  Controls: () => null,
  Handle: ({ type }: { type: string }) => <i data-handle={type} />,
  Position: { Left: "left", Right: "right" }
}));

function ticket(id: string, depends_on: string[] = []): TicketSummary {
  return {
    id, status: "pending", executor: "orch-render", bound: "30m", claimed_at: "", claimed_by: "",
    depends_on, unreadable: false,
    readiness: { state: "waiting", dependencies: depends_on, explanation: `${id} waits`, cause: "pending_dependency", causal_chain: [id] }
  };
}

describe("RunGraph", () => {
  it("connects every canonical dependency to real node endpoints", () => {
    const { container } = render(<RunGraph tickets={[ticket("A"), ticket("B", ["A"])]} />);
    expect(screen.getByLabelText("A to B: canonical dependency")).not.toBeNull();
    expect(container.querySelectorAll('[data-handle="target"]')).toHaveLength(2);
    expect(container.querySelectorAll('[data-handle="source"]')).toHaveLength(2);
  });
});
