import type { FeatureData, PollingPolicy } from "../../../shared/transport/types";
import type { RunMapModel } from "../model";
import type { RunMapRoute } from "../route";
import { project } from "./project";
import { request } from "./request";
import { schema, type RunMapPayload } from "./schema";

export function polling(model: RunMapModel | null): PollingPolicy {
  return { intervalMs: model?.run?.active ? 750 : 2500 };
}

export const data: FeatureData<RunMapRoute, RunMapPayload, RunMapModel> = {
  schema,
  request,
  polling,
  project,
};
