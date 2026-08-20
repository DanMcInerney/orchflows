import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { FeatureState } from "../../../shared/transport/types";
import { detailFixture } from "../fixtures";
import type { WorkflowDetailModel } from "../model";
import { WorkflowDetailView } from "../view/WorkflowDetailView";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const ready = (model: WorkflowDetailModel): FeatureState<WorkflowDetailModel> => ({
  status: "ready",
  model,
  error: null,
});

describe("WorkflowDetailView", () => {
  it("renders exact typed topology and an identical complete ordered companion", () => {
    const { container } = render(
      <WorkflowDetailView route={{ workflowId: "evolve", fixture: "complex-loop" }} state={ready(detailFixture)} />,
    );

    expect(screen.getByRole("heading", { name: "evolve" })).not.toBeNull();
    expect(screen.getByRole("link", { name: "Workflows" }).getAttribute("href")).toBe("/workflows?fixture=complex-loop");
    const graph = screen.getByRole("group", { name: "Exact topology for evolve" });
    expect(within(graph).getAllByRole("button")).toHaveLength(
      detailFixture.nodes.length + detailFixture.edges.length,
    );
    expect(graph.querySelectorAll("[data-workflow-connector]")).toHaveLength(detailFixture.edges.length);
    expect(graph.querySelectorAll("path[data-edge-kind='loop'][data-self-loop='true']")).toHaveLength(1);

    const companion = screen.getByRole("region", { name: "Complete ordered topology" });
    const companionNodes = within(companion).getByRole("list", { name: "Workflow nodes" });
    const companionRelations = within(companion).getByRole("list", { name: "Workflow relations" });
    expect(within(companionNodes).getAllByRole("listitem")).toHaveLength(detailFixture.nodes.length);
    expect(within(companionRelations).getAllByRole("listitem").map((item) => item.getAttribute("data-edge-id"))).toEqual(
      detailFixture.relations.map((relation) => relation.id),
    );
    expect(within(companion).getByText("02-campaign loops to 02-campaign — bounded generations")).not.toBeNull();
    expect(within(companion).getAllByRole("link", { name: /^View source for / })).toHaveLength(
      detailFixture.nodes.filter((node) => node.sourceId).length,
    );
    expect(container.querySelector(".workflow-detail__layout")?.firstElementChild?.classList.contains("workflow-detail__graph-panel")).toBe(true);
  });

  it("renders the inspector before the graph in compact DOM and tab order", () => {
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: query === "(max-width: 1024px)",
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    const { container } = render(
      <WorkflowDetailView route={{ workflowId: "evolve", fixture: "complex-loop" }} state={ready(detailFixture)} />,
    );
    const layout = container.querySelector(".workflow-detail__layout");
    expect(layout?.firstElementChild?.classList.contains("workflow-inspector")).toBe(true);
    expect(layout?.lastElementChild?.classList.contains("workflow-detail__graph-panel")).toBe(true);
  });

  it("selects graph nodes and edges with Enter or Space in a persistent inspector", async () => {
    const user = userEvent.setup();
    render(<WorkflowDetailView route={{ workflowId: "evolve", fixture: "complex-loop" }} state={ready(detailFixture)} />);

    const campaign = screen.getByRole("button", { name: "Select work 02-campaign" });
    const graph = screen.getByRole("group", { name: "Exact topology for evolve" });
    Object.defineProperty(graph, "clientWidth", { configurable: true, value: 320 });
    campaign.focus();
    await user.keyboard("{Enter}");
    await waitFor(() => expect(graph.scrollLeft).toBeGreaterThan(0));
    expect(screen.getByRole("heading", { name: "02-campaign" })).not.toBeNull();
    const inspector = screen.getByRole("complementary", { name: "02-campaign" });
    expect(within(inspector).getByRole("link", { name: "View source for 02-campaign" }).getAttribute("href")).toBe(
      "/workflows/evolve/sources/src_campaign?fixture=complex-loop",
    );

    const loop = screen.getByRole("button", { name: "Select loop 02-campaign loops to 02-campaign" });
    loop.focus();
    await user.keyboard(" ");
    expect(screen.getByRole("heading", { name: "bounded generations" })).not.toBeNull();
    expect(screen.getByText("Loop relation")).not.toBeNull();
  });

  it("keeps canonical diagnostics explicit and mutation controls absent", () => {
    const unreadable: WorkflowDetailModel = {
      ...detailFixture,
      diagnostics: [{
        code: "unresolved-reference",
        subjectId: "skill:missing",
        message: "Executor reference could not be resolved.",
      }],
    };
    render(<WorkflowDetailView route={{ workflowId: "evolve", fixture: "unreadable" }} state={ready(unreadable)} />);

    expect(screen.getByRole("heading", { name: "1 topology diagnostic" })).not.toBeNull();
    expect(screen.getByText("Executor reference could not be resolved.")).not.toBeNull();
    expect(screen.queryByRole("button", { name: /edit|delete|run|retry|start/i })).toBeNull();
  });

  it("explains a definition with no projected topology", () => {
    render(
      <WorkflowDetailView
        route={{ workflowId: "unreadable", fixture: "empty" }}
        state={ready({ id: "unreadable", type: "workflow-skill", tier: "T1", nodes: [], edges: [], relations: [], diagnostics: [] })}
      />,
    );

    expect(screen.getByRole("heading", { name: "Topology is unavailable" })).not.toBeNull();
    expect(screen.getByText(/no exact nodes or relations/i)).not.toBeNull();
    expect(screen.getByRole("link", { name: "Back to Workflows" })).not.toBeNull();
  });
});
