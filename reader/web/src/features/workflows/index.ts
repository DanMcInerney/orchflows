import { createElement, type ComponentType } from "react";

import type { FeatureState } from "../../shared/transport/types";
import { catalogData, detailData, sourceData } from "./data/useFeed";
import { catalogFixture, detailFixture, sourceFixture, workflowSkillDetailFixture } from "./fixtures";
import type {
  WorkflowCatalogModel,
  WorkflowDetailModel,
  WorkflowSourceModel,
} from "./model";
import { detailRoute, listRoute, sourceRoute } from "./route";
import type {
  WorkflowDetailRoute,
  WorkflowListRoute,
  WorkflowSourceRoute,
} from "./route";

export * from "./model";
export * from "./route";
export { catalogData, detailData, sourceData } from "./data/useFeed";

type ViewProps<Route, Model> = {
  route: Route;
  state: FeatureState<Model>;
};

function withFixture<Route extends { fixture: string }, Model>(
  load: () => Promise<{ default: ComponentType<ViewProps<Route, Model>> }>,
  select: (route: Route) => FeatureState<Model> | null,
) {
  return async () => {
    const { default: View } = await load();
    const BoundView = (props: ViewProps<Route, Model>) => createElement(View, {
      ...props,
      state: select(props.route) ?? props.state,
    });
    return { default: BoundView };
  };
}

function ready<Model>(model: Model): FeatureState<Model> {
  return { status: "ready", model, error: null };
}

function catalogState(route: WorkflowListRoute): FeatureState<WorkflowCatalogModel> | null {
  if (route.fixture === "populated" || route.fixture === "catalog") return ready(catalogFixture);
  if (route.fixture === "empty") return ready({ workflows: [] });
  if (route.fixture === "unreadable") {
    return {
      status: "stale",
      model: catalogFixture,
      error: { code: "invalid-payload", message: "Some canonical definitions could not be read." },
    };
  }
  return null;
}

function detailState(route: WorkflowDetailRoute): FeatureState<WorkflowDetailModel> | null {
  if (route.fixture === "complex-loop") return ready(detailFixture);
  if (route.fixture === "callable") return ready(workflowSkillDetailFixture);
  if (route.fixture === "empty") {
    return ready({
      id: route.workflowId,
      type: "workflow-skill",
      tier: "T1",
      nodes: [],
      edges: [],
      relations: [],
      diagnostics: [],
    });
  }
  if (route.fixture === "unreadable") {
    return ready({
      ...detailFixture,
      id: route.workflowId,
      diagnostics: [{
        code: "unresolved-reference",
        subjectId: "skill:unresolved",
        message: "A referenced definition could not be resolved.",
      }],
    });
  }
  return null;
}

function sourceState(route: WorkflowSourceRoute): FeatureState<WorkflowSourceModel> | null {
  if (route.fixture === "populated" || route.fixture === "source") {
    return ready({ ...sourceFixture, id: route.sourceId });
  }
  if (route.fixture === "missing-source") {
    return {
      status: "error",
      model: null,
      error: { code: "not-found", message: "Source not found." },
    };
  }
  if (route.fixture === "unreadable-source") {
    return {
      status: "error",
      model: null,
      error: { code: "invalid-payload", message: "Source is unreadable." },
    };
  }
  return null;
}

export const list = {
  route: listRoute,
  data: catalogData,
  loadView: withFixture(
    () => import("./view/WorkflowCatalogView"),
    catalogState,
  ),
};

export const detail = {
  route: detailRoute,
  data: detailData,
  loadView: withFixture(
    () => import("./view/WorkflowDetailView"),
    detailState,
  ),
};

export const source = {
  route: sourceRoute,
  data: sourceData,
  loadView: withFixture(
    () => import("./view/WorkflowSourceView"),
    sourceState,
  ),
};

export const styles = "./styles.css";
