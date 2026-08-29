import type { FeatureData, PollingPolicy } from "../../../shared/transport/types";
import type { SessionsModel } from "../model";
import type { SessionsRoute } from "../route";
import { project } from "./project";
import { request } from "./request";
import { schema, type SessionsPayload } from "./schema";

export function polling(_model: SessionsModel | null): PollingPolicy {
  return { intervalMs: 2500 };
}

export const data: FeatureData<SessionsRoute, SessionsPayload, SessionsModel> = {
  schema,
  request,
  polling,
  project,
};
