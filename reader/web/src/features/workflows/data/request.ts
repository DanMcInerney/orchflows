import type { RequestSpec } from "../../../shared/transport/types";
import type {
  WorkflowDetailRoute,
  WorkflowListRoute,
  WorkflowSourceRoute,
} from "../route";

export function catalogRequest(_route: WorkflowListRoute): RequestSpec {
  return { url: "/api/v1/workflows" };
}

export function detailRequest(route: WorkflowDetailRoute): RequestSpec {
  return { url: `/api/v1/workflows/${encodeURIComponent(route.workflowId)}` };
}

export function sourceRequest(route: WorkflowSourceRoute): RequestSpec {
  return {
    url: `/api/v1/workflows/${encodeURIComponent(route.workflowId)}/sources/${encodeURIComponent(route.sourceId)}`,
  };
}
