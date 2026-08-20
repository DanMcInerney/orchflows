export interface FrictionPayload {
  schema: "orchflows.friction.v1";
  friction: Record<string, unknown>;
}

function record(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

export function schema(value: unknown): FrictionPayload {
  if (!record(value) || value.schema !== "orchflows.friction.v1" || !record(value.friction)) {
    throw new Error("invalid friction payload");
  }
  return value as unknown as FrictionPayload;
}
