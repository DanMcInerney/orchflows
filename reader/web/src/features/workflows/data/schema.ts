import type {
  DetailEdgeKind,
  DetailNodeKind,
  SummaryEdgeKind,
  WorkflowDiagnosticCode,
  WorkflowSourceModel,
} from "../model";

export interface SummaryNodePayload {
  id: string;
  label: string;
}

export interface SummaryEdgePayload {
  source: string;
  target: string;
  kind: SummaryEdgeKind;
}

export interface SummaryPayload {
  nodes: SummaryNodePayload[];
  edges: SummaryEdgePayload[];
}

interface CatalogItemPayloadBase {
  id: string;
  description: string;
  summary: SummaryPayload;
}

export interface CompositionCatalogPayload extends CatalogItemPayloadBase {
  type: "composition";
  entry: "routed" | "named";
}

export interface WorkflowSkillCatalogPayload extends CatalogItemPayloadBase {
  type: "workflow-skill";
  entry: "callable";
}

export type CatalogItemPayload = CompositionCatalogPayload | WorkflowSkillCatalogPayload;

export interface WorkflowCatalogPayload {
  schema: "orchflows.workflow-catalog.v1";
  workflows: CatalogItemPayload[];
}

export interface DetailNodePayload {
  id: string;
  kind: DetailNodeKind;
  label: string;
  source_id?: string;
}

export interface DetailEdgePayload {
  id: string;
  kind: DetailEdgeKind;
  from: string;
  to: string;
  label: string;
}

export interface DiagnosticPayload {
  code: WorkflowDiagnosticCode;
  subject_id: string;
  message: string;
}

export interface WorkflowDetailPayload {
  schema: "orchflows.workflow-detail.v1";
  id: string;
  type: "composition" | "workflow-skill";
  nodes: DetailNodePayload[];
  edges: DetailEdgePayload[];
  relations: DetailEdgePayload[];
  diagnostics: DiagnosticPayload[];
}

export type WorkflowSourcePayload = WorkflowSourceModel;

function record(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function exact(value: unknown, required: readonly string[], optional: readonly string[] = []): value is Record<string, unknown> {
  if (!record(value)) return false;
  const keys = Object.keys(value);
  return required.every((key) => Object.hasOwn(value, key))
    && keys.every((key) => required.includes(key) || optional.includes(key));
}

function string(value: unknown): value is string {
  return typeof value === "string";
}

function oneOf<const Value extends string>(value: unknown, values: readonly Value[]): value is Value {
  return typeof value === "string" && values.includes(value as Value);
}

function summaryNode(value: unknown): value is SummaryNodePayload {
  return exact(value, ["id", "label"])
    && string(value.id)
    && string(value.label);
}

function summaryEdge(value: unknown): value is SummaryEdgePayload {
  return exact(value, ["source", "target", "kind"])
    && string(value.source)
    && string(value.target)
    && oneOf(value.kind, ["sequence", "branch", "loop"]);
}

function summary(value: unknown): value is SummaryPayload {
  return exact(value, ["nodes", "edges"])
    && Array.isArray(value.nodes)
    && value.nodes.every(summaryNode)
    && Array.isArray(value.edges)
    && value.edges.every(summaryEdge);
}

function catalogItem(value: unknown): value is CatalogItemPayload {
  if (!exact(value, ["id", "type", "entry", "description", "summary"])
    || !string(value.id)
    || !string(value.description)
    || !summary(value.summary)) return false;
  return value.type === "composition"
    ? oneOf(value.entry, ["routed", "named"])
    : value.type === "workflow-skill" && value.entry === "callable";
}

function detailNode(value: unknown): value is DetailNodePayload {
  return exact(value, ["id", "kind", "label"], ["source_id"])
    && string(value.id)
    && oneOf(value.kind, ["workflow", "work", "skill", "script"])
    && string(value.label)
    && (!Object.hasOwn(value, "source_id") || string(value.source_id));
}

function detailEdge(value: unknown): value is DetailEdgePayload {
  return exact(value, ["id", "kind", "from", "to", "label"])
    && string(value.id)
    && oneOf(value.kind, ["dependency", "executor", "skill-call", "script-call", "loop"])
    && string(value.from)
    && string(value.to)
    && string(value.label);
}

function diagnostic(value: unknown): value is DiagnosticPayload {
  return exact(value, ["code", "subject_id", "message"])
    && oneOf(value.code, ["duplicate-node", "dangling-edge", "unresolved-reference"])
    && string(value.subject_id)
    && string(value.message);
}

export function catalogSchema(value: unknown): WorkflowCatalogPayload {
  if (!exact(value, ["schema", "workflows"])
    || value.schema !== "orchflows.workflow-catalog.v1"
    || !Array.isArray(value.workflows)
    || !value.workflows.every(catalogItem)) {
    throw new Error("invalid workflow catalog payload");
  }
  return value as unknown as WorkflowCatalogPayload;
}

export function detailSchema(value: unknown): WorkflowDetailPayload {
  if (!exact(value, ["schema", "id", "type", "nodes", "edges", "relations", "diagnostics"])
    || value.schema !== "orchflows.workflow-detail.v1"
    || !string(value.id)
    || !oneOf(value.type, ["composition", "workflow-skill"])
    || !Array.isArray(value.nodes)
    || !value.nodes.every(detailNode)
    || !Array.isArray(value.edges)
    || !value.edges.every(detailEdge)
    || !Array.isArray(value.relations)
    || !value.relations.every(detailEdge)
    || !Array.isArray(value.diagnostics)
    || !value.diagnostics.every(diagnostic)) {
    throw new Error("invalid workflow detail payload");
  }
  return value as unknown as WorkflowDetailPayload;
}

export function sourceSchema(value: unknown): WorkflowSourcePayload {
  if (!exact(value, ["schema", "id", "text", "sha256", "language", "redacted"])
    || value.schema !== "orchflows.workflow-source.v1"
    || !string(value.id)
    || !string(value.text)
    || !string(value.sha256)
    || !string(value.language)
    || typeof value.redacted !== "boolean") {
    throw new Error("invalid workflow source payload");
  }
  return value as unknown as WorkflowSourcePayload;
}
