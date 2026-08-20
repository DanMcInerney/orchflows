import type {
  WorkflowCatalogModel,
  WorkflowCatalogItem,
  WorkflowDetailModel,
  WorkflowSourceModel,
  WorkflowSummary,
} from "./model";

function flow(
  labels: readonly string[],
  extras: WorkflowSummary["edges"] = [],
): WorkflowSummary {
  const nodes = labels.map((label, index) => ({ id: `n${index + 1}`, label }));
  const sequence = nodes.slice(1).map((node, index) => ({
    source: nodes[index].id,
    target: node.id,
    kind: "sequence" as const,
  }));
  return { nodes, edges: [...sequence, ...extras] };
}

const workflows: WorkflowCatalogItem[] = [
  {
    id: "fix",
    type: "composition",
    tier: "T3",
    entry: "routed",
    description: "Use for a bug or defect with an unknown or unverified cause.",
    summary: flow(["Observe failure", "Find cause", "Repair", "Guard regression"]),
  },
  {
    id: "benchmaker",
    type: "composition",
    tier: "T3",
    entry: "named",
    description: "Build and qualify a runnable benchmark.",
    summary: flow(["Define task", "Build cases", "Qualify benchmark"]),
  },
  {
    id: "evolve",
    type: "composition",
    tier: "T3",
    entry: "named",
    description: "Run bounded candidate generations against a frozen evaluation; manual only.",
    summary: flow(
      ["Freeze evaluation", "Generate candidates", "Judge blind", "Select winner"],
      [{ source: "n4", target: "n2", kind: "loop" }],
    ),
  },
  {
    id: "drift-canary",
    type: "composition",
    tier: "T3",
    entry: "named",
    description: "Detect drift after a model, effort, or host change.",
    summary: flow(["Freeze baseline", "Run canary", "Compare verdicts"]),
  },
  {
    id: "renovate",
    type: "composition",
    tier: "T3",
    entry: "named",
    description: "Improve a workspace without a user-supplied specification.",
    summary: flow(["Inspect workspace", "Choose improvement", "Deliver change"]),
  },
  {
    id: "self-improve",
    type: "composition",
    tier: "T3",
    entry: "named",
    description: "Turn friction and run evidence into one qualified, landed proposal.",
    summary: flow(["Mine evidence", "Draft proposal", "Qualify", "Land winner"]),
  },
  {
    id: "skill-tournament",
    type: "composition",
    tier: "T3",
    entry: "named",
    description: "Evolve one skill against its prequalified benchmark.",
    summary: flow(
      ["Load benchmark", "Mutate skill", "Score candidates", "Keep winner"],
      [{ source: "n4", target: "n2", kind: "loop" }],
    ),
  },
  {
    id: "orch-build",
    type: "workflow-skill",
    tier: "T1",
    entry: "callable",
    description: "Use for any new or amended skill, pack, or contract.",
    summary: flow(["Specify item", "Build artifact", "Run admission"]),
  },
  {
    id: "orch-eval-design",
    type: "workflow-skill",
    tier: "T1",
    entry: "callable",
    description: "Use before benchmark construction or direct judged scoring.",
    summary: flow(["Name behavior", "Design evidence", "Freeze rubric"]),
  },
  {
    id: "orch-fixture",
    type: "workflow-skill",
    tier: "T1",
    entry: "callable",
    description: "Use when a proven ticket should guard against drift.",
    summary: flow(["Select proof", "Create fixture", "Verify discrimination"]),
  },
  {
    id: "orch-repair",
    type: "workflow-skill",
    tier: "T1",
    entry: "callable",
    description: "Use inside a gate or for any accepted defect set.",
    summary: flow(["Group causes", "Repair causes", "Re-run checks"]),
  },
  {
    id: "orch-self-improve",
    type: "workflow-skill",
    tier: "T1",
    entry: "callable",
    description: "Use as the mining stub, or alone when proposals suffice.",
    summary: flow(["Read friction", "Find pattern", "Propose change"]),
  },
  {
    id: "orch-spec",
    type: "workflow-skill",
    tier: "T1",
    entry: "callable",
    description: "Use before any delivery run.",
    summary: flow(["Gather evidence", "Resolve decisions", "Issue root ticket"]),
  },
  {
    id: "orch-triage",
    type: "workflow-skill",
    tier: "T1",
    entry: "callable",
    description: "Use before queued items are dispatched.",
    summary: flow(["Read queue", "Classify readiness", "Route work"]),
  },
];

export const catalogFixture: WorkflowCatalogModel = { workflows };

export const detailFixture: WorkflowDetailModel = {
  id: "evolve",
  type: "composition",
  tier: "T3",
  nodes: [],
  edges: [],
  relations: [],
  diagnostics: [],
};

export const sourceFixture: WorkflowSourceModel = {
  schema: "orchflows.workflow-source.v1",
  id: "src_fixture",
  text: "# fixture\n",
  sha256: "0".repeat(64),
  language: "markdown",
  redacted: false,
};
