import type { TicketDetail } from "../model";

export interface InspectorPayload {
  schema: "orchflows.inspector.v1";
  run: Record<string, unknown> | null;
  ticket: TicketDetail | null;
}

function record(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function strings(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function optionalText(value: unknown): boolean {
  return value === undefined || typeof value === "string";
}

function executorSource(value: unknown): boolean {
  return value === undefined || (record(value)
    && ["available", "unavailable"].includes(String(value.state))
    && optionalText(value.workflow_id)
    && optionalText(value.source_id)
    && optionalText(value.label)
    && optionalText(value.reason));
}

function artifacts(value: unknown): boolean {
  return value === undefined || (record(value)
    && ["rows", "unavailable"].includes(String(value.state))
    && Array.isArray(value.rows)
    && value.rows.every((item) => record(item)
      && typeof item.artifact_id === "string"
      && typeof item.label === "string"
      && ["available", "unavailable"].includes(String(item.state))
      && optionalText(item.media_type)
      && optionalText(item.reason))
    && optionalText(value.reason));
}

function judgment(value: unknown): boolean {
  return value === undefined || (record(value)
    && typeof value.rationale_identity === "string"
    && ["available", "unavailable"].includes(String(value.rationale_state))
    && optionalText(value.rationale_reason));
}

function ticket(value: unknown): value is TicketDetail {
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
    && strings(value.readiness.causal_chain)
    && record(value.sections)
    && record(value.verification)
    && Array.isArray(value.verification.rows)
    && strings(value.inputs)
    && strings(value.write_scope)
    && typeof value.pack === "string"
    && Array.isArray(value.history)
    && typeof value.raw === "string"
    && executorSource(value.executor_source)
    && artifacts(value.artifacts)
    && judgment(value.judgment);
}

export function schema(value: unknown): InspectorPayload {
  if (!record(value)
    || value.schema !== "orchflows.inspector.v1"
    || (value.run !== null && !record(value.run))
    || (value.ticket !== null && !ticket(value.ticket))) {
    throw new Error("invalid inspector payload");
  }
  return value as unknown as InspectorPayload;
}
