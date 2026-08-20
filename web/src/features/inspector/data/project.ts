import type { InspectorModel } from "../model";
import type { InspectorPayload } from "./schema";

export function project(payload: InspectorPayload): InspectorModel {
  return { run: payload.run, ticket: payload.ticket };
}
