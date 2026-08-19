export interface SessionSummary {
  id: string;
  title: string;
  modified: string;
  agentCount: number;
  diagnostics: string[];
  client: string;
  project: string;
}

export interface SessionsModel {
  items: SessionSummary[];
  diagnostics: string[];
  empty: boolean;
}

function record(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function textList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function count(value: unknown): number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0 ? value : 0;
}

function session(value: unknown): SessionSummary | null {
  if (!record(value)) return null;
  const id = text(value.id);
  if (!id) return null;
  return {
    id,
    title: text(value.title),
    modified: text(value.modified),
    agentCount: count(value.agent_count),
    diagnostics: textList(value.diagnostics),
    client: text(value.client),
    project: text(value.project)
  };
}

export function sessionsModel(value: unknown): SessionsModel {
  if (!record(value)) return { items: [], diagnostics: [], empty: true };
  const items = Array.isArray(value.items)
    ? value.items.map(session).filter((item): item is SessionSummary => item !== null)
    : [];
  return {
    items,
    diagnostics: textList(value.diagnostics),
    empty: value.empty === true || items.length === 0
  };
}

export function fixtureSessions(model: SessionsModel, fixture: string): SessionsModel {
  if (fixture === "empty") return { items: [], diagnostics: [], empty: true };
  if (fixture !== "diagnostic") return model;
  const diagnosticItems = model.items.filter((item) => item.diagnostics.length > 0);
  const itemDiagnostics = [...new Set(diagnosticItems.flatMap((item) => item.diagnostics))];
  return {
    items: diagnosticItems.length ? diagnosticItems : model.items,
    diagnostics: model.diagnostics.length
      ? model.diagnostics
      : itemDiagnostics.length
        ? itemDiagnostics
        : ["Some session metadata could not be read; unavailable fields remain unknown."],
    empty: model.items.length === 0
  };
}

export function sessionLabel(item: SessionSummary): string {
  return item.title || "Untitled session";
}
