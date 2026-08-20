import type { RunDetail, RunSummary, TicketSummary } from "../model";

export interface RunMapPayload {
  schema: "orchflows.run-map.v1";
  runs: RunSummary[];
  run: RunDetail | null;
}

function record(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function strings(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function ticket(value: unknown): value is TicketSummary {
  return record(value)
    && record(value.readiness)
    && typeof value.id === "string"
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

function summary(value: unknown): value is RunSummary {
  return record(value)
    && typeof value.id === "string"
    && typeof value.ticket_count === "number"
    && typeof value.active === "boolean";
}

function detail(value: unknown): value is RunDetail {
  return record(value)
    && typeof value.id === "string"
    && typeof value.active === "boolean"
    && Array.isArray(value.tickets)
    && value.tickets.every(ticket)
    && Array.isArray(value.diagnostics)
    && record(value.counts);
}

export function schema(value: unknown): RunMapPayload {
  if (!record(value)
    || value.schema !== "orchflows.run-map.v1"
    || !Array.isArray(value.runs)
    || !value.runs.every(summary)
    || (value.run !== null && !detail(value.run))) {
    throw new Error("invalid run-map payload");
  }
  return value as unknown as RunMapPayload;
}
