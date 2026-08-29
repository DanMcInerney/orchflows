import type {
  CompositionCatalogItem,
  CompositionDetailModel,
  WorkflowCatalogItem,
  WorkflowCatalogModel,
  WorkflowDetailEdge,
  WorkflowDetailModel,
  WorkflowDetailNode,
  WorkflowDiagnostic,
  WorkflowSkillCatalogItem,
  WorkflowSkillDetailModel,
  WorkflowSourceModel,
} from "../model";
import type {
  CatalogItemPayload,
  DetailEdgePayload,
  DetailNodePayload,
  DiagnosticPayload,
  WorkflowCatalogPayload,
  WorkflowDetailPayload,
  WorkflowSourcePayload,
} from "./schema";

function catalogItem(value: CatalogItemPayload): WorkflowCatalogItem {
  const shared = {
    id: value.id,
    description: value.description,
    summary: {
      nodes: value.summary.nodes.map((node) => ({ ...node })),
      edges: value.summary.edges.map((edge) => ({ ...edge })),
    },
  };
  if (value.type === "composition") {
    return { ...shared, type: value.type, tier: "T3", entry: value.entry } satisfies CompositionCatalogItem;
  }
  return { ...shared, type: value.type, tier: "T1", entry: value.entry } satisfies WorkflowSkillCatalogItem;
}

function node(value: DetailNodePayload): WorkflowDetailNode {
  const projected: WorkflowDetailNode = {
    id: value.id,
    kind: value.kind,
    label: value.label,
  };
  if (value.source_id !== undefined) projected.sourceId = value.source_id;
  return projected;
}

function edge(value: DetailEdgePayload): WorkflowDetailEdge {
  return { ...value };
}

function diagnostic(value: DiagnosticPayload): WorkflowDiagnostic {
  return {
    code: value.code,
    subjectId: value.subject_id,
    message: value.message,
  };
}

export function projectCatalog(payload: WorkflowCatalogPayload): WorkflowCatalogModel {
  return { workflows: payload.workflows.map(catalogItem) };
}

export function projectDetail(payload: WorkflowDetailPayload): WorkflowDetailModel {
  const shared = {
    id: payload.id,
    nodes: payload.nodes.map(node),
    edges: payload.edges.map(edge),
    relations: payload.relations.map(edge),
    diagnostics: payload.diagnostics.map(diagnostic),
  };
  if (payload.type === "composition") {
    return { ...shared, type: payload.type, tier: "T3" } satisfies CompositionDetailModel;
  }
  return { ...shared, type: payload.type, tier: "T1" } satisfies WorkflowSkillDetailModel;
}

export function projectSource(payload: WorkflowSourcePayload): WorkflowSourceModel {
  return { ...payload };
}
