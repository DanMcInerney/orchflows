export interface SessionsPayload {
  schema: "orchflows.sessions.v1";
  sessions: Record<string, unknown>;
}

function record(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

export function schema(value: unknown): SessionsPayload {
  if (!record(value) || value.schema !== "orchflows.sessions.v1" || !record(value.sessions)) {
    throw new Error("invalid sessions payload");
  }
  return value as unknown as SessionsPayload;
}
