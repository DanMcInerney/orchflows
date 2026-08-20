import { isSessionDetail, type SessionDetail } from "../topology";

export interface SessionGraphPayload {
  schema: "orchflows.session-graph.v1";
  session: SessionDetail | null;
}

function record(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

export function schema(value: unknown): SessionGraphPayload {
  if (!record(value)
    || value.schema !== "orchflows.session-graph.v1"
    || (value.session !== null && !isSessionDetail(value.session))) {
    throw new Error("invalid session-graph payload");
  }
  return value as unknown as SessionGraphPayload;
}
