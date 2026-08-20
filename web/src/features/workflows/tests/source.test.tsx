import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { FeatureState } from "../../../shared/transport/types";
import { sourceFixture } from "../fixtures";
import type { WorkflowSourceModel } from "../model";
import { WorkflowSourceView } from "../view/WorkflowSourceView";

afterEach(cleanup);

const ready = (model: WorkflowSourceModel): FeatureState<WorkflowSourceModel> => ({
  status: "ready",
  model,
  error: null,
});

const failed = (code: "not-found" | "invalid-payload" | "unavailable", message: string): FeatureState<WorkflowSourceModel> => ({
  status: "error",
  model: null,
  error: { code, message },
});

const route = (fixture: string) => ({ workflowId: "evolve", sourceId: "src_campaign", fixture });

describe("WorkflowSourceView", () => {
  it("renders only closed metadata and inert source text", () => {
    const { container } = render(<WorkflowSourceView route={route("source")} state={ready(sourceFixture)} />);

    expect(screen.getByRole("navigation", { name: "Breadcrumb" }).textContent).toBe("Workflows/evolve/src_campaign");
    expect(screen.getByRole("link", { name: "Workflows" }).getAttribute("href")).toBe("/workflows?fixture=source");
    expect(screen.getByRole("link", { name: "evolve" }).getAttribute("href")).toBe("/workflows/evolve?fixture=source");
    expect(screen.getByRole("link", { name: "Back to evolve" }).getAttribute("href")).toBe("/workflows/evolve?fixture=source");
    expect(screen.getByRole("heading", { name: "src_campaign" })).not.toBeNull();
    expect(screen.getByText("markdown")).not.toBeNull();
    expect(screen.getByText(sourceFixture.sha256)).not.toBeNull();
    expect(screen.getByText("Host details redacted")).not.toBeNull();

    const code = screen.getByLabelText("Source text for src_campaign");
    expect(code.textContent).toBe(sourceFixture.text);
    expect(container.querySelector("script, iframe")).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("wraps and contains a long opaque source breadcrumb", () => {
    const longSourceId = `src_${"opaque".repeat(20)}`;
    render(<WorkflowSourceView route={{ workflowId: "evolve", sourceId: longSourceId, fixture: "source" }} state={ready(sourceFixture)} />);

    const breadcrumb = screen.getByRole("navigation", { name: "Breadcrumb" });
    const current = breadcrumb.querySelector("[aria-current='page']");
    expect(getComputedStyle(breadcrumb).flexWrap).toBe("wrap");
    expect(getComputedStyle(current as Element).minWidth).toBe("0px");
    expect(getComputedStyle(current as Element).overflowWrap).toBe("anywhere");
  });

  it("keeps navigation operable while a missing source stays generic", () => {
    const { container } = render(
      <WorkflowSourceView
        route={route("missing-source")}
        state={failed("not-found", "C:\\private\\library\\secret.md did not exist")}
      />,
    );

    expect(screen.getByRole("heading", { name: "Source not found" })).not.toBeNull();
    expect(screen.getByText(/not associated with this workflow/i)).not.toBeNull();
    expect(screen.getByRole("link", { name: "Back to evolve" })).not.toBeNull();
    expect(container.textContent).not.toContain("C:\\private");
    expect(container.querySelector("pre")).toBeNull();
  });

  it("distinguishes unreadable content without leaking the reader failure", () => {
    const { container } = render(
      <WorkflowSourceView
        route={route("unreadable-source")}
        state={failed("invalid-payload", "UnicodeDecodeError at host path")}
      />,
    );

    expect(screen.getByRole("heading", { name: "Source is unreadable" })).not.toBeNull();
    expect(screen.getByText(/safe source metadata could not be projected/i)).not.toBeNull();
    expect(container.textContent).not.toContain("UnicodeDecodeError");
    expect(screen.getByRole("link", { name: "Back to evolve" })).not.toBeNull();
  });
});
