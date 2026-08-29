import type { FeatureData, PollingPolicy } from "../../../shared/transport/types";
import type { InspectorModel } from "../model";
import type { InspectorRoute } from "../route";
import { project } from "./project";
import { request } from "./request";
import { schema, type InspectorPayload } from "./schema";

export function polling(model: InspectorModel | null): PollingPolicy {
  return { intervalMs: model?.ticket?.status === "claimed" ? 750 : 2500 };
}

export const data: FeatureData<InspectorRoute, InspectorPayload, InspectorModel> = {
  schema,
  request,
  polling,
  project,
};
