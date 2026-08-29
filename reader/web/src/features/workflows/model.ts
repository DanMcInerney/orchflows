export type SummaryEdgeKind = "sequence" | "branch" | "loop";
export type DetailNodeKind = "workflow" | "work" | "skill" | "script";
export type DetailEdgeKind = "dependency" | "executor" | "skill-call" | "script-call" | "loop";
export type WorkflowDiagnosticCode = "duplicate-node" | "dangling-edge" | "unresolved-reference";

export interface SummaryNode {
  id: string;
  label: string;
}

export interface SummaryEdge {
  source: string;
  target: string;
  kind: SummaryEdgeKind;
}

export interface WorkflowSummary {
  nodes: SummaryNode[];
  edges: SummaryEdge[];
}

interface WorkflowCatalogItemBase {
  id: string;
  description: string;
  summary: WorkflowSummary;
}

export interface CompositionCatalogItem extends WorkflowCatalogItemBase {
  type: "composition";
  tier: "T3";
  entry: "routed" | "named";
}

export interface WorkflowSkillCatalogItem extends WorkflowCatalogItemBase {
  type: "workflow-skill";
  tier: "T1";
  entry: "callable";
}

export type WorkflowCatalogItem = CompositionCatalogItem | WorkflowSkillCatalogItem;

export interface WorkflowCatalogModel {
  workflows: WorkflowCatalogItem[];
}

export interface WorkflowDetailNode {
  id: string;
  kind: DetailNodeKind;
  label: string;
  sourceId?: string;
}

export interface WorkflowDetailEdge {
  id: string;
  kind: DetailEdgeKind;
  from: string;
  to: string;
  label: string;
}

export interface WorkflowDiagnostic {
  code: WorkflowDiagnosticCode;
  subjectId: string;
  message: string;
}

interface WorkflowDetailBase {
  id: string;
  nodes: WorkflowDetailNode[];
  edges: WorkflowDetailEdge[];
  relations: WorkflowDetailEdge[];
  diagnostics: WorkflowDiagnostic[];
}

export interface CompositionDetailModel extends WorkflowDetailBase {
  type: "composition";
  tier: "T3";
}

export interface WorkflowSkillDetailModel extends WorkflowDetailBase {
  type: "workflow-skill";
  tier: "T1";
}

export type WorkflowDetailModel = CompositionDetailModel | WorkflowSkillDetailModel;

export interface WorkflowSourceModel {
  schema: "orchflows.workflow-source.v1";
  id: string;
  text: string;
  sha256: string;
  language: string;
  redacted: boolean;
}
