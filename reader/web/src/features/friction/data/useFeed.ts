import type { FeatureData, PollingPolicy } from "../../../shared/transport/types";
import type { FrictionModel } from "../model";
import type { FrictionRoute } from "../route";
import { project } from "./project";
import { request } from "./request";
import { schema, type FrictionPayload } from "./schema";

export function polling(_model: FrictionModel | null): PollingPolicy {
  return { intervalMs: 2500 };
}

export const data: FeatureData<FrictionRoute, FrictionPayload, FrictionModel> = {
  schema,
  request,
  polling,
  project,
};
