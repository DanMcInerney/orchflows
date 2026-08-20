import type { FeatureData, PollingPolicy } from "../../../shared/transport/types";
import type { SessionGraphRoute } from "../route";
import type { SessionGraphModel } from "../topology";
import { project } from "./project";
import { request } from "./request";
import { schema, type SessionGraphPayload } from "./schema";

export function polling(model: SessionGraphModel | null): PollingPolicy {
  return { intervalMs: model?.session?.agents.some((agent) => agent.state === "running") ? 750 : 2500 };
}

export const data: FeatureData<SessionGraphRoute, SessionGraphPayload, SessionGraphModel> = {
  schema,
  request,
  polling,
  project,
};
