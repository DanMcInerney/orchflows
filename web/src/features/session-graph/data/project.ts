import type { SessionGraphModel } from "../topology";
import type { SessionGraphPayload } from "./schema";

export function project(payload: SessionGraphPayload): SessionGraphModel {
  return { session: payload.session };
}
