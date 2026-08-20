import type { FeatureData, PollingPolicy } from "../../../shared/transport/types";
import type { NowModel } from "../model";
import type { NowRoute } from "../route";
import { project } from "./project";
import { request } from "./request";
import { schema, type NowPayload } from "./schema";

export function polling(model: NowModel | null): PollingPolicy {
  return { intervalMs: model?.runs.some((run) => run.tickets.some((ticket) => ticket.status === "claimed")) ? 750 : 2500 };
}

export const data: FeatureData<NowRoute, NowPayload, NowModel> = {
  schema,
  request,
  polling,
  project,
};
