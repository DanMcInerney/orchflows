import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ExperienceSnapshot } from "../../api/schema";
import type { LocationState } from "../../state/location";
import { SessionGraphView } from "./SessionGraphView";

vi.mock("@xyflow/react", async () => {
  const actual = await vi.importActual<typeof import("@xyflow/react")>("@xyflow/react");
  return {
    ...actual,
    ReactFlowProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    Background: () => null,
    Controls: () => <div aria-label="Session graph zoom controls" />,
    MiniMap: ({ ariaLabel }: { ariaLabel: string }) => <div aria-label={ariaLabel} />,
    ReactFlow: ({ nodes, edges, nodeTypes, onNodeClick, children, ...props }: any) => {
      const NodeComponent = nodeTypes.sessionAgent;
      return (
        <div aria-label={props["aria-label"]}>
          {nodes.map((node: any) => (
            <button key={node.id} aria-label={node.ariaLabel} onClick={() => onNodeClick({}, node)}>
              <NodeComponent data={node.data} selected={node.selected} />
            </button>
          ))}
          {edges.map((edge: any) => <span key={edge.id} aria-label={edge.ariaLabel}>{edge.label}</span>)}
          {children}
        </div>
      );
    }
  };
});

const location: LocationState = {
  view: "session-graph",
  run: "",
  ticket: "",
  session: "safe-session",
  fixture: "populated"
};

const snapshot = {
  schema: "orchflows.experience.v1",
  navigation: [],
  selection: { view: "session-graph", run: "", ticket: "", session: "safe-session" },
  runs: [], run: null, ticket: null,
  sessions: { items: [], diagnostics: [], empty: false },
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
  friction: { items: [], skipped: 0, unreadable: 0 }
} as unknown as ExperienceSnapshot;

afterEach(cleanup);

describe("SessionGraphView", () => {
  it("renders responsive safe topology with keyboard-reachable selection and provenance", () => {
    render(<SessionGraphView snapshot={snapshot} location={location} />);

    expect(screen.getByRole("heading", { name: "Safe session title" })).not.toBeNull();
    expect(screen.getByLabelText("Session agent topology")).not.toBeNull();
    expect(screen.getByLabelText("Session topology minimap")).not.toBeNull();
    expect(screen.getByLabelText("Session graph zoom controls")).not.toBeNull();
    expect(screen.getByLabelText(/agent-one to agent-two: recorded parent/)).not.toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /Select agent agent-two/ }));
    expect(screen.getByText("called, no result yet")).not.toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /Select agent agent-one/ }));
    expect(screen.getByRole("heading", { name: "agent-one" })).not.toBeNull();
    expect(screen.getByText("result recorded")).not.toBeNull();
  });

  it("enforces the content and path wall by projecting only closed metadata fields", () => {
    const { container } = render(<SessionGraphView snapshot={snapshot} location={location} />);
    expect(container.textContent).not.toContain("PRIVATE PROMPT");
    expect(container.textContent).not.toContain("PRIVATE TOOL OUTPUT");
    expect(container.textContent).not.toContain("C:/private/worktree");
    expect(screen.queryByRole("button", { name: /start|edit|delete|send/i })).toBeNull();
  });

  it("names missing safe topology without guessing", () => {
    render(<SessionGraphView snapshot={{ ...snapshot, session: null }} location={location} />);
    expect(screen.getByRole("heading", { name: "Session metadata is unavailable" })).not.toBeNull();
    expect(screen.getByText("safe-session")).not.toBeNull();
  });
});
