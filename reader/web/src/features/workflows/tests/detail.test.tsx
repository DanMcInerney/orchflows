import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { FeatureState } from "../../../shared/transport/types";
import { detailFixture, workflowSkillDetailFixture } from "../fixtures";
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

    expect(screen.getByRole("heading", { name: "evolve", level: 1 })).not.toBeNull();
    expect(detailFixture.nodes.map((node) => node.id)).toEqual([
      "workflow:evolve",
      "work:evolve/00-eval",
      "work:evolve/01-eligibility",
      "work:evolve/02-campaign",
      "work:evolve/03-result",
      "skill:orch-eval-design",
      "skill:orch-execute",
      "skill:orch-verify",
    ]);
    expect(screen.getByRole("link", { name: "Workflows" }).getAttribute("href")).toBe("/workflows?fixture=complex-loop");
    const graph = screen.getByRole("group", { name: "Exact topology for evolve" });
    expect(screen.getByRole("heading", { name: "Skills called, step by step" })).not.toBeNull();
    expect(screen.getByText(/runtime tickets are created later/i)).not.toBeNull();
    expect(within(graph).getAllByRole("button").filter((button) => button.classList.contains("workflow-graph__edge"))).toHaveLength(detailFixture.edges.length);
    expect(new Set(Array.from(graph.querySelectorAll("[data-node-id]")).map((node) => node.getAttribute("data-node-id")))).toEqual(
      new Set(detailFixture.nodes.map((node) => node.id)),
    );
    expect(graph.querySelectorAll("[data-workflow-connector]")).toHaveLength(detailFixture.edges.length);
    expect(graph.querySelectorAll("[data-edge-kind='loop'][data-self-loop='true']")).toHaveLength(1);
    expect(within(graph).getAllByRole("button", { name: "Select Called skill orch-verify" })).toHaveLength(2);
    expect(within(graph).getAllByRole("button", { name: /^Select Definition-time ticket template / })).toHaveLength(4);
    expect(within(graph).getByRole("button", { name: "Select Composition definition evolve" })).not.toBeNull();
    expect(within(graph).queryByRole("heading", { name: "Additional canonical calls" })).toBeNull();

    const companion = screen.getByRole("region", { name: "Complete ordered topology" });
    const companionNodes = within(companion).getByRole("list", { name: "Workflow nodes" });
    const companionRelations = within(companion).getByRole("list", { name: "Workflow relations" });
    expect(within(companionNodes).getAllByRole("listitem")).toHaveLength(detailFixture.nodes.length);
    expect(within(companion).getByRole("list", { name: "Workflow steps" }).children).toHaveLength(4);
    expect(within(companionRelations).getAllByRole("listitem").map((item) => item.getAttribute("data-edge-id"))).toEqual(
      detailFixture.relations.map((relation) => relation.id),
    );
    expect(within(companion).getByText(
      "02-campaign loops to 02-campaign — Write candidates; verify eligibility; score blind; select by the frozen rule; repeat {{bound}}",
    )).not.toBeNull();
    expect(within(companion).getAllByRole("link", { name: /^View source for / })).toHaveLength(
      detailFixture.nodes.filter((node) => node.sourceId).length,
    );
    expect(container.querySelector(".workflow-detail__layout")?.firstElementChild?.classList.contains("workflow-detail__graph-panel")).toBe(true);
  });

  it("keeps the primary graph before the announced inspector at the compact breakpoint", () => {
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
    expect(layout?.firstElementChild?.classList.contains("workflow-detail__graph-panel")).toBe(true);
    expect(layout?.lastElementChild?.classList.contains("workflow-inspector")).toBe(true);
    expect(screen.getByRole("complementary").getAttribute("aria-live")).toBe("polite");
  });

  it("selects graph nodes and edges with Enter or Space in a persistent inspector", async () => {
    const user = userEvent.setup();
    render(<WorkflowDetailView route={{ workflowId: "evolve", fixture: "complex-loop" }} state={ready(detailFixture)} />);

    const campaign = screen.getByRole("button", { name: "Select Definition-time ticket template 02-campaign" });
    campaign.focus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("heading", { name: "02-campaign" })).not.toBeNull();
    const inspector = screen.getByRole("complementary", { name: "02-campaign" });
    expect(within(inspector).getByRole("link", { name: "View source for 02-campaign" }).getAttribute("href")).toBe(
      "/workflows/evolve/sources/src_sTfMymQaOuMdgYI2T3yzH5i9hPfDmnZgMGZlkCwmbB4?fixture=complex-loop",
    );

    const loop = screen.getByRole("button", { name: "Select loop relation: 02-campaign loops to 02-campaign" });
    loop.focus();
    await user.keyboard(" ");
    expect(screen.getByRole("heading", { name: /Write candidates; verify eligibility/ })).not.toBeNull();
    expect(screen.getByText("Loop relation")).not.toBeNull();
  });

  it("keeps reused executor occurrences distinct and scrolls the chosen control into view", async () => {
    const user = userEvent.setup();
    const scrollIntoView = vi.fn();
    Object.defineProperty(Element.prototype, "scrollIntoView", { configurable: true, value: scrollIntoView });
    try {
      render(<WorkflowDetailView route={{ workflowId: "evolve", fixture: "complex-loop" }} state={ready(detailFixture)} />);

      const occurrences = screen.getAllByRole("button", { name: "Select Called skill orch-verify" });
      await user.click(occurrences[1]);

      expect(occurrences[0].getAttribute("aria-pressed")).toBe("false");
      expect(occurrences[1].getAttribute("aria-pressed")).toBe("true");
      expect(scrollIntoView).toHaveBeenCalledTimes(1);
      expect(scrollIntoView.mock.instances[0]).toBe(occurrences[1]);
    } finally {
      delete (Element.prototype as { scrollIntoView?: Element["scrollIntoView"] }).scrollIntoView;
    }
  });

  it("shows a callable workflow as ordered skill and script calls", () => {
    render(
      <WorkflowDetailView
        route={{ workflowId: "orch-spec", fixture: "callable" }}
        state={ready(workflowSkillDetailFixture)}
      />,
    );

    expect(screen.getByRole("heading", { name: "Skills and scripts called" })).not.toBeNull();
    expect(workflowSkillDetailFixture.nodes.map((node) => node.id)).toEqual([
      "workflow:orch-spec",
      "skill:orch-decompose",
      "skill:orch-frontier",
      "skill:orch-integrate",
      "skill:orch-investigate",
      "script:bin/tickets.py",
    ]);
    const graph = screen.getByRole("group", { name: "Exact topology for orch-spec" });
    expect(within(graph).getByRole("button", { name: "Select Workflow definition orch-spec" })).not.toBeNull();
    expect(within(graph).getAllByRole("listitem")).toHaveLength(5);
    expect(within(graph).getByRole("button", { name: "Select Called skill orch-investigate" })).not.toBeNull();
    expect(within(graph).getByRole("button", { name: "Select Called script bin/tickets.py" })).not.toBeNull();
    expect(graph.querySelectorAll("[data-workflow-connector]")).toHaveLength(workflowSkillDetailFixture.edges.length);
    expect(screen.getByRole("list", { name: "Workflow calls" }).children).toHaveLength(5);
    expect(Array.from(graph.querySelectorAll("[data-call-source]")).map((item) => ({
      source: item.getAttribute("data-call-source"),
      target: item.getAttribute("data-call-target"),
    }))).toEqual(workflowSkillDetailFixture.edges.map((edge) => ({ source: edge.from, target: edge.to })));
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
