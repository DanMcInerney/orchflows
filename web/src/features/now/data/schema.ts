import type { NowRunPayload, NowTicket } from "../model";

export interface NowPayload {
  schema: "orchflows.now.v1";
  runs: NowRunPayload[];
}

function record(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function strings(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function ticket(value: unknown): value is NowTicket {
  if (!record(value) || !record(value.readiness)) return false;
  return typeof value.id === "string"
    && typeof value.status === "string"
    && typeof value.executor === "string"
    && typeof value.bound === "string"
    && typeof value.claimed_at === "string"
    && typeof value.claimed_by === "string"
    && typeof value.unreadable === "boolean"
    && strings(value.depends_on)
    && typeof value.readiness.state === "string"
    && strings(value.readiness.dependencies)
    && typeof value.readiness.explanation === "string"
    && typeof value.readiness.cause === "string"
    && strings(value.readiness.causal_chain);
}

function run(value: unknown): value is NowRunPayload {
  return record(value)
    && typeof value.id === "string"
    && typeof value.ticket_count === "number"
    && typeof value.active === "boolean"
    && typeof value.objective === "string"
    && typeof value.repository === "string"
    && typeof value.client === "string"
    && typeof value.last_activity === "string"
    && typeof value.unreadable === "boolean"
    && Array.isArray(value.tickets)
    && value.tickets.every(ticket);
}

export function schema(value: unknown): NowPayload {
  if (!record(value) || value.schema !== "orchflows.now.v1" || !Array.isArray(value.runs) || !value.runs.every(run)) {
    throw new Error("invalid Now payload");
  }
  return value as unknown as NowPayload;
}
