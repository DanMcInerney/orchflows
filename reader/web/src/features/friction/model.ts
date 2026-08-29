export interface FrictionRecord {
  ts?: string;
  host?: string;
  observed?: string;
  expected?: string;
  run?: string;
  ticket?: string;
}

export interface FrictionModel {
  items: FrictionRecord[];
  skipped: number;
  unreadable: number;
}

const FRICTION_FIELDS = ["ts", "host", "observed", "expected", "run", "ticket"] as const;
const WINDOWS_PATH = /\b[A-Za-z]:\\(?:[^\s<>"']+)/g;
const HOME_PATH = /\/(?:Users|home)\/(?:[^\s<>"']+)/g;

function plainText(value: unknown): string {
  if (typeof value !== "string") return "";
  return value.replace(WINDOWS_PATH, "[redacted path]").replace(HOME_PATH, "[redacted path]");
}

export function closedFrictionRecord(value: unknown): FrictionRecord | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const source = value as Record<string, unknown>;
  const record: FrictionRecord = {};
  for (const field of FRICTION_FIELDS) {
    const projected = plainText(source[field]);
    if (projected) record[field] = projected;
  }
  return Object.keys(record).length ? record : null;
}

function count(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? Math.max(0, value) : 0;
}

export function frictionModel(value: Record<string, unknown>): FrictionModel {
  const items = Array.isArray(value.items)
    ? value.items.map(closedFrictionRecord).filter((item): item is FrictionRecord => item !== null)
    : [];
  return { items, skipped: count(value.skipped), unreadable: count(value.unreadable) };
}

export const model = { frictionModel, closedFrictionRecord };
