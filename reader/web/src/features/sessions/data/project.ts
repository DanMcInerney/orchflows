import { sessionsModel, type SessionsModel } from "../model";
import type { SessionsPayload } from "./schema";

export function project(payload: SessionsPayload): SessionsModel {
  return sessionsModel(payload.sessions);
}
