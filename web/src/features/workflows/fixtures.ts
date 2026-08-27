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
  nodes: [
    { id: "work:evolve/00-eval", kind: "work", label: "00-eval", sourceId: "src_eval" },
    { id: "work:evolve/01-eligibility", kind: "work", label: "01-eligibility", sourceId: "src_eligibility" },
    { id: "work:evolve/02-campaign", kind: "work", label: "02-campaign", sourceId: "src_campaign" },
    { id: "work:evolve/03-result", kind: "work", label: "03-result", sourceId: "src_result" },
    { id: "skill:orch-eval-design", kind: "skill", label: "orch-eval-design", sourceId: "src_eval_design" },
    { id: "skill:orch-verify", kind: "skill", label: "orch-verify", sourceId: "src_verify" },
    { id: "skill:orch-loop", kind: "skill", label: "orch-loop", sourceId: "src_loop" },
  ],
  edges: [
    { id: "dep-00-01", kind: "dependency", from: "work:evolve/00-eval", to: "work:evolve/01-eligibility", label: "evaluation before eligibility" },
    { id: "dep-01-02", kind: "dependency", from: "work:evolve/01-eligibility", to: "work:evolve/02-campaign", label: "eligibility before campaign" },
    { id: "dep-02-03", kind: "dependency", from: "work:evolve/02-campaign", to: "work:evolve/03-result", label: "campaign before result" },
    { id: "exec-00", kind: "executor", from: "work:evolve/00-eval", to: "skill:orch-eval-design", label: "executed by" },
    { id: "exec-01", kind: "executor", from: "work:evolve/01-eligibility", to: "skill:orch-verify", label: "executed by" },
    { id: "exec-02", kind: "executor", from: "work:evolve/02-campaign", to: "skill:orch-loop", label: "executed by" },
    { id: "exec-03", kind: "executor", from: "work:evolve/03-result", to: "skill:orch-verify", label: "executed by" },
    { id: "loop-02", kind: "loop", from: "work:evolve/02-campaign", to: "work:evolve/02-campaign", label: "bounded generations" },
  ],
  relations: [
    { id: "dep-00-01", kind: "dependency", from: "work:evolve/00-eval", to: "work:evolve/01-eligibility", label: "evaluation before eligibility" },
    { id: "exec-00", kind: "executor", from: "work:evolve/00-eval", to: "skill:orch-eval-design", label: "executed by" },
    { id: "dep-01-02", kind: "dependency", from: "work:evolve/01-eligibility", to: "work:evolve/02-campaign", label: "eligibility before campaign" },
    { id: "exec-01", kind: "executor", from: "work:evolve/01-eligibility", to: "skill:orch-verify", label: "executed by" },
    { id: "dep-02-03", kind: "dependency", from: "work:evolve/02-campaign", to: "work:evolve/03-result", label: "campaign before result" },
    { id: "exec-02", kind: "executor", from: "work:evolve/02-campaign", to: "skill:orch-loop", label: "executed by" },
    { id: "loop-02", kind: "loop", from: "work:evolve/02-campaign", to: "work:evolve/02-campaign", label: "bounded generations" },
    { id: "exec-03", kind: "executor", from: "work:evolve/03-result", to: "skill:orch-verify", label: "executed by" },
  ],
  diagnostics: [],
};

export const sourceFixture: WorkflowSourceModel = {
  schema: "orchflows.workflow-source.v1",
  id: "src_fixture",
  text: "# Campaign\n\n<button>Run me</button>\n<script>doNotRun()</script>\n",
  sha256: "0".repeat(64),
  language: "markdown",
  redacted: true,
};
