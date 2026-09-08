import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Edge, Node } from "@xyflow/react";
import { SessionGraphView } from "./SessionGraphView";
import type { SessionGraphModel } from "./topology";

vi.mock("@xyflow/react", async () => {
  const actual = await vi.importActual<typeof import("@xyflow/react")>("@xyflow/react");
  return {
    ...actual,
    ReactFlowProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    Background: () => null,
    Handle: ({ "aria-label": ariaLabel }: { "aria-label": string }) => <span aria-label={ariaLabel} />,
    Controls: () => <div aria-label="Session graph zoom controls" />,
    ReactFlow: ({ nodes, edges, nodeTypes, onNodeClick, children, ...props }: {
      nodes?: Array<Node<Record<string, unknown>> & { ariaLabel?: string }>;
      edges?: Array<Edge & { ariaLabel?: string }>;
      nodeTypes: Record<string, (props: {
        id: string;
        data: Record<string, unknown>;
        selected?: boolean;
      }) => ReactNode>;
      onNodeClick: (event: unknown, node: Node<Record<string, unknown>>) => void;
      children?: ReactNode;
      "aria-label"?: string;
    }) => {
      const NodeComponent = nodeTypes.sessionAgent;
      return (
        <div aria-label={props["aria-label"]}>
          {(nodes ?? []).map((node) => (
            <button key={node.id} aria-label={node.ariaLabel} onClick={() => onNodeClick({}, node)}>
              <NodeComponent id={node.id} data={node.data} selected={node.selected ?? false} />
            </button>
          ))}
          {(edges ?? []).map((edge) => <span key={edge.id} aria-label={edge.ariaLabel} />)}
          {children}
        </div>
      );
    }
  };
});

const route = {
  session: "safe-session",
  fixture: "populated"
};

const model = {
  session: {
    id: "safe-session",
    title: "Safe session title",
    modified: "1000000",
    agent_count: 2,
    diagnostics: [],
    agents: [
      { id: "agent-one", type: "orch-worker", depth: 1, parent: "", modified: "2000000", state: "finished", evidence: "result recorded", unreadable: false },
      { id: "agent-two", type: "Explore", depth: 2, parent: "one", modified: "3000000", state: "running", evidence: "called, no result yet", unreadable: false }
    ],
    prompt: "PRIVATE PROMPT MUST NOT RENDER",
    cwd: "C:/private/worktree",
    tool_output: "PRIVATE TOOL OUTPUT MUST NOT RENDER"
  },
} as unknown as SessionGraphModel;

const ready = (value: SessionGraphModel) => ({ status: "ready", model: value, error: null } as const);

afterEach(cleanup);

describe("SessionGraphView", () => {
  it("renders responsive safe topology with keyboard-reachable selection and provenance", () => {
    render(<SessionGraphView state={ready(model)} route={route} />);

    expect(screen.getByRole("heading", { name: "Safe session title" })).not.toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Show full topology/ }));
    expect(screen.getByLabelText("Session agent topology")).not.toBeNull();
    expect(screen.getByLabelText(/Session topology minimap/)).not.toBeNull();
    expect(screen.getByLabelText("Session graph zoom controls")).not.toBeNull();
    expect(screen.getByLabelText(/agent-one to agent-two: recorded parent/)).not.toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /Select agent agent-two/ }));
    expect(screen.getByText("called, no result yet")).not.toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /Select agent agent-one/ }));
    expect(screen.getByRole("heading", { name: "agent-one" })).not.toBeNull();
    expect(screen.getByText("result recorded")).not.toBeNull();
  });

  it("enforces the content and path wall by projecting only closed metadata fields", () => {
    const { container } = render(<SessionGraphView state={ready(model)} route={route} />);
    expect(container.textContent).not.toContain("PRIVATE PROMPT");
    expect(container.textContent).not.toContain("PRIVATE TOOL OUTPUT");
    expect(container.textContent).not.toContain("C:/private/worktree");
    expect(screen.queryByRole("button", { name: /start|edit|delete|send/i })).toBeNull();
  });

  it("names missing safe topology without guessing", () => {
    render(<SessionGraphView state={ready({ session: null })} route={route} />);
    expect(screen.getByRole("heading", { name: "Session metadata is unavailable" })).not.toBeNull();
    expect(screen.getByText("safe-session")).not.toBeNull();
  });
});


it("keeps all 24 agents reachable, selected across refresh, and inside minimap bounds", async () => {
  const user = userEvent.setup();
  const session = { ...model.session!, agent_count: 24, agents: Array.from({ length: 24 }, (_, i) => ({ ...model.session!.agents[0], id: `agent-${i}`, depth: i < 20 ? 1 : i - 18, parent: i < 20 ? "" : `agent-${i - 1}` })) };
  const { rerender } = render(<SessionGraphView state={ready({ session })} route={route} />);
  const list = screen.getByLabelText("All session agents");
  expect(within(list).getAllByRole("button")).toHaveLength(25);
  expect(screen.queryByLabelText("Session agent topology")).toBeNull();
  const last = within(list).getByRole("button", { name: /^agent-23,/ });
  last.focus();
  await user.keyboard("{Enter}");
  expect(screen.getByRole("heading", { name: "agent-23" })).not.toBeNull();
  await user.click(within(list).getByRole("button", { name: /^agent-0,/ }));
  last.focus();
  await user.keyboard(" ");
  expect(last.getAttribute("aria-pressed")).toBe("true");
  rerender(<SessionGraphView state={ready({ session: { ...session, modified: "new" } })} route={route} />);
  expect(screen.getByRole("heading", { name: "agent-23" })).not.toBeNull();
  expect(document.activeElement).toBe(last);
  rerender(<SessionGraphView state={ready({ session: { ...session, agents: session.agents.slice(0, -1) } })} route={route} />);
  expect(screen.queryByRole("heading", { name: "agent-23" })).toBeNull();
  expect(within(list).getAllByRole("button").filter((button) => button.getAttribute("aria-pressed") === "true")).toHaveLength(1);
  rerender(<SessionGraphView state={ready({ session })} route={route} />);
  await user.click(screen.getByRole("button", { name: /Show full topology/ }));
  const map = screen.getByLabelText(/Session topology minimap/);
  const [, , width, height] = map.getAttribute("viewBox")!.split(" ").map(Number);
  const rects = map.querySelectorAll("rect");
  expect(rects.length).toBe(25);
  rects.forEach((rect) => {
    expect(Number(rect.getAttribute("x")) + Number(rect.getAttribute("width"))).toBeLessThan(width);
    expect(Number(rect.getAttribute("y")) + Number(rect.getAttribute("height"))).toBeLessThan(height);
  });
});
