import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ObserveApp } from "./ObserveApp";

vi.mock("@xyflow/react", () => ({
  Background: () => null,
  Controls: () => null,
  ReactFlow: ({ nodes, nodesDraggable, nodesConnectable, onNodesChange }: {
    nodes: Array<{ id: string; data: { label: string }; selected?: boolean }>;
    nodesDraggable: boolean;
    nodesConnectable: boolean;
    onNodesChange: (changes: Array<{ id: string; type: "select"; selected: boolean }>) => void;
  }) => (
    <div
      data-testid="flow"
      data-draggable={String(nodesDraggable)}
      data-connectable={String(nodesConnectable)}
    >
      {nodes.map((node) => (
        <button
          key={node.id}
          aria-label={`Select ${node.data.label}`}
          aria-pressed={node.selected}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              onNodesChange([{ id: node.id, type: "select", selected: true }]);
            }
          }}
        >
          {node.data.label}
        </button>
      ))}
    </div>
  ),
  ReactFlowProvider: ({ children }: { children: React.ReactNode }) => children
}));

vi.mock("./layout", () => ({
  layoutSnapshot: vi.fn(async (snapshot) => snapshot.nodes.map((node: {
    id: string;
    label: string;
    status: string;
  }) => ({
    id: node.id,
    data: { label: node.label, status: node.status },
    position: { x: 0, y: 0 }
  })))
}));

const first = {
  revision: "one",
  active: true,
  nodes: [
    { id: "A", label: "Acquire", status: "complete" },
    { id: "B", label: "Build", status: "claimed" }
  ],
  edges: [{ id: "A-B", source: "A", target: "B" }]
};

const second = {
  ...first,
  revision: "two",
  nodes: first.nodes.map((node) => node.id === "B" ? { ...node, status: "complete" } : node)
};

describe("ObserveApp", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    let call = 0;
    vi.stubGlobal("fetch", vi.fn(async () => {
      call += 1;
      if (call === 2) {
        return new Response(null, { status: 304, headers: { ETag: '"one"' } });
      }
      const snapshot = call > 2 ? second : first;
      return new Response(JSON.stringify(snapshot), {
        status: 200,
        headers: { "Content-Type": "application/json", ETag: `"${snapshot.revision}"` }
      });
    }));
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("keeps keyboard selection across ETag refresh and exposes no editing affordance", async () => {
    render(<ObserveApp />);
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });
    const build = screen.getByRole("button", { name: "Select Build" });
    fireEvent.keyDown(build, { key: "Enter" });
    expect(build.getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByTestId("flow").getAttribute("data-draggable")).toBe("false");
    expect(screen.getByTestId("flow").getAttribute("data-connectable")).toBe("false");
    expect(screen.getByRole("main").getAttribute("data-mode")).toBe("observe");

    await vi.advanceTimersByTimeAsync(2_500);
    expect(screen.queryByText("revision two")).not.toBeNull();
    expect(
      screen.getByRole("button", { name: "Select Build" }).getAttribute("aria-pressed")
    ).toBe("true");
  });
});
