import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { FeatureState } from "../../../shared/transport/types";
import { catalogFixture } from "../fixtures";
import type { WorkflowCatalogModel } from "../model";
import { WorkflowCatalogView } from "../view/WorkflowCatalogView";

afterEach(cleanup);

const ready = (model: WorkflowCatalogModel): FeatureState<WorkflowCatalogModel> => ({
  status: "ready",
  model,
  error: null,
});

describe("WorkflowCatalogView", () => {
  it("presents every canonical definition in one glanceable list without run instances", () => {
    render(<WorkflowCatalogView route={{ fixture: "catalog" }} state={ready(catalogFixture)} />);

    const catalog = screen.getByRole("list", { name: "Workflow definitions" });
    const rows = catalog.querySelectorAll(":scope > li");
    expect(rows).toHaveLength(14);
    expect(screen.getAllByText("T3 composition")).toHaveLength(7);
    expect(screen.getAllByText("T1 workflow skill")).toHaveLength(7);

    const fix = screen.getByRole("link", { name: "fix" });
    expect(fix.getAttribute("href")).toBe("/workflows/fix?fixture=catalog");
    expect(fix.closest("li")?.textContent).toContain("unknown or unverified cause");
    expect(fix.closest("li")?.textContent).toContain("Routed");
    expect(screen.queryByRole("link", { name: /run-/i })).toBeNull();
    expect(document.querySelector("a[href^='/runs/']")).toBeNull();
  });

  it("gives each noninteractive summary the same complete ordered nonvisual meaning", () => {
    render(<WorkflowCatalogView route={{ fixture: "catalog" }} state={ready(catalogFixture)} />);

    const summaries = screen.getAllByRole("figure");
    expect(summaries).toHaveLength(14);
    for (const summary of summaries) {
      expect(within(summary).queryByRole("button")).toBeNull();
      expect(within(summary).queryByRole("link")).toBeNull();
    }

    const fixSummary = screen.getByRole("figure", { name: "Summary flow for fix" });
    const equivalent = within(fixSummary).getByRole("list", { name: "Nonvisual summary for fix" });
    expect(within(equivalent).getAllByRole("listitem").map((item) => item.textContent)).toEqual([
      "Step: Observe failure",
      "Step: Find cause",
      "Step: Repair",
      "Step: Guard regression",
      "Observe failure continues to Find cause",
      "Find cause continues to Repair",
      "Repair continues to Guard regression",
    ]);
  });

  it("explains the meaningful empty state", () => {
    render(<WorkflowCatalogView route={{ fixture: "empty" }} state={ready({ workflows: [] })} />);

    expect(screen.getByRole("heading", { name: "No workflow definitions available" })).not.toBeNull();
    expect(screen.getByText(/canonical workflow catalog is empty/i)).not.toBeNull();
  });
});
