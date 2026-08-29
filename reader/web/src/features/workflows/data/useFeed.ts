import type { FeatureData, PollingPolicy } from "../../../shared/transport/types";
import type {
  WorkflowCatalogModel,
  WorkflowDetailModel,
  WorkflowSourceModel,
} from "../model";
import type {
  WorkflowDetailRoute,
  WorkflowListRoute,
  WorkflowSourceRoute,
} from "../route";
import { projectCatalog, projectDetail, projectSource } from "./project";
import { catalogRequest, detailRequest, sourceRequest } from "./request";
import {
  catalogSchema,
  detailSchema,
  sourceSchema,
  type WorkflowCatalogPayload,
  type WorkflowDetailPayload,
  type WorkflowSourcePayload,
} from "./schema";

const DEFINITION_POLL_INTERVAL_MS = 5000;

export function catalogPolling(_model: WorkflowCatalogModel | null): PollingPolicy {
  return { intervalMs: DEFINITION_POLL_INTERVAL_MS };
}

export function detailPolling(_model: WorkflowDetailModel | null): PollingPolicy {
  return { intervalMs: DEFINITION_POLL_INTERVAL_MS };
}

export function sourcePolling(_model: WorkflowSourceModel | null): PollingPolicy {
  return false;
}

export const catalogData: FeatureData<
  WorkflowListRoute,
  WorkflowCatalogPayload,
  WorkflowCatalogModel
> = {
  schema: catalogSchema,
  request: catalogRequest,
  polling: catalogPolling,
  project: projectCatalog,
};

export const detailData: FeatureData<
  WorkflowDetailRoute,
  WorkflowDetailPayload,
  WorkflowDetailModel
> = {
  schema: detailSchema,
  request: detailRequest,
  polling: detailPolling,
  project: projectDetail,
};

export const sourceData: FeatureData<
  WorkflowSourceRoute,
  WorkflowSourcePayload,
  WorkflowSourceModel
> = {
  schema: sourceSchema,
  request: sourceRequest,
  polling: sourcePolling,
  project: projectSource,
};
