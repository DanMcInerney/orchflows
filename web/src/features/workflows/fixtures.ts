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
    { id: "workflow:evolve", kind: "workflow", label: "evolve", sourceId: "src_qazoJDvYxEK7CQoZUGXqibjv5a4gy0GFtfXuBOkn1Tk" },
    { id: "work:evolve/00-eval", kind: "work", label: "00-eval", sourceId: "src_yhgOi3Trjz0n3No_3fKAYlgV_JbksUuKN00lJT-zuPc" },
    { id: "work:evolve/01-eligibility", kind: "work", label: "01-eligibility", sourceId: "src_F649jwCSVo97etZfJy4BH88ExcHuJOAAKFebtgkc8IM" },
    { id: "work:evolve/02-campaign", kind: "work", label: "02-campaign", sourceId: "src_sTfMymQaOuMdgYI2T3yzH5i9hPfDmnZgMGZlkCwmbB4" },
    { id: "work:evolve/03-result", kind: "work", label: "03-result", sourceId: "src_ZH4IilRjF9hW8pJceEVaUzdD8oxy2fiEFZDH0HkHYhw" },
    { id: "skill:orch-eval-design", kind: "skill", label: "orch-eval-design", sourceId: "src_9sFenMwi49U5GskF-nlpyE6nu1BdzPHLjILISnO5O6M" },
    { id: "skill:orch-loop", kind: "skill", label: "orch-loop", sourceId: "src_OSUHs7ocg3tQ1GV2BFshHNik4XuhtF5Ip5nZkWpzebk" },
    { id: "skill:orch-verify", kind: "skill", label: "orch-verify", sourceId: "src_a-stZE2iVFVCou6ulzokItq-2V_jk7MXKj_tfDMzfc4" },
  ],
  edges: [
    { id: "edge:dependency:work%3Aevolve%2F00-eval:work%3Aevolve%2F01-eligibility", kind: "dependency", from: "work:evolve/00-eval", to: "work:evolve/01-eligibility", label: "continues to" },
    { id: "edge:executor:work%3Aevolve%2F00-eval:skill%3Aorch-eval-design", kind: "executor", from: "work:evolve/00-eval", to: "skill:orch-eval-design", label: "executes with" },
    { id: "edge:dependency:work%3Aevolve%2F01-eligibility:work%3Aevolve%2F02-campaign", kind: "dependency", from: "work:evolve/01-eligibility", to: "work:evolve/02-campaign", label: "continues to" },
    { id: "edge:executor:work%3Aevolve%2F01-eligibility:skill%3Aorch-verify", kind: "executor", from: "work:evolve/01-eligibility", to: "skill:orch-verify", label: "executes with" },
    { id: "edge:dependency:work%3Aevolve%2F02-campaign:work%3Aevolve%2F03-result", kind: "dependency", from: "work:evolve/02-campaign", to: "work:evolve/03-result", label: "continues to" },
    { id: "edge:executor:work%3Aevolve%2F02-campaign:skill%3Aorch-loop", kind: "executor", from: "work:evolve/02-campaign", to: "skill:orch-loop", label: "executes with" },
    { id: "edge:loop:work%3Aevolve%2F02-campaign:work%3Aevolve%2F02-campaign", kind: "loop", from: "work:evolve/02-campaign", to: "work:evolve/02-campaign", label: "Write candidates; verify eligibility; score blind; select by the frozen rule; repeat {{bound}}" },
    { id: "edge:executor:work%3Aevolve%2F03-result:skill%3Aorch-verify", kind: "executor", from: "work:evolve/03-result", to: "skill:orch-verify", label: "executes with" },
  ],
  relations: [
    { id: "edge:dependency:work%3Aevolve%2F00-eval:work%3Aevolve%2F01-eligibility", kind: "dependency", from: "work:evolve/00-eval", to: "work:evolve/01-eligibility", label: "continues to" },
    { id: "edge:executor:work%3Aevolve%2F00-eval:skill%3Aorch-eval-design", kind: "executor", from: "work:evolve/00-eval", to: "skill:orch-eval-design", label: "executes with" },
    { id: "edge:dependency:work%3Aevolve%2F01-eligibility:work%3Aevolve%2F02-campaign", kind: "dependency", from: "work:evolve/01-eligibility", to: "work:evolve/02-campaign", label: "continues to" },
    { id: "edge:executor:work%3Aevolve%2F01-eligibility:skill%3Aorch-verify", kind: "executor", from: "work:evolve/01-eligibility", to: "skill:orch-verify", label: "executes with" },
    { id: "edge:dependency:work%3Aevolve%2F02-campaign:work%3Aevolve%2F03-result", kind: "dependency", from: "work:evolve/02-campaign", to: "work:evolve/03-result", label: "continues to" },
    { id: "edge:executor:work%3Aevolve%2F02-campaign:skill%3Aorch-loop", kind: "executor", from: "work:evolve/02-campaign", to: "skill:orch-loop", label: "executes with" },
    { id: "edge:loop:work%3Aevolve%2F02-campaign:work%3Aevolve%2F02-campaign", kind: "loop", from: "work:evolve/02-campaign", to: "work:evolve/02-campaign", label: "Write candidates; verify eligibility; score blind; select by the frozen rule; repeat {{bound}}" },
    { id: "edge:executor:work%3Aevolve%2F03-result:skill%3Aorch-verify", kind: "executor", from: "work:evolve/03-result", to: "skill:orch-verify", label: "executes with" },
  ],
  diagnostics: [],
};

export const workflowSkillDetailFixture: WorkflowDetailModel = {
  id: "orch-spec",
  type: "workflow-skill",
  tier: "T1",
  nodes: [
    { id: "workflow:orch-spec", kind: "workflow", label: "orch-spec", sourceId: "src_0VUYksiNsyKSpde5CZiVpt4DwBC8_h4Z93DsTtYSJew" },
    { id: "skill:orch-decompose", kind: "skill", label: "orch-decompose", sourceId: "src_pjqipWcCb9e-TFl30-lSYbaHgv5pNBeYMdeU88x6HkU" },
    { id: "skill:orch-frontier", kind: "skill", label: "orch-frontier", sourceId: "src_iceqWPOkLMm0YGo55R8wqP7Zeli2OTh8Tmmat2W3UPs" },
    { id: "skill:orch-integrate", kind: "skill", label: "orch-integrate", sourceId: "src_k8zEnYSjCPHMUu2_juTsuT-FOsdpQma_5CcHMQvuawM" },
    { id: "skill:orch-investigate", kind: "skill", label: "orch-investigate", sourceId: "src_C-lkIYg0qiiGkrXqkRYkx7c8ZtdzdkWqELW6KoSkkv4" },
    { id: "script:bin/tickets.py", kind: "script", label: "bin/tickets.py", sourceId: "src_Pixqbalm62YNOliAPAfwWxT8aNee0m56zhPFHm4WHOk" },
  ],
  edges: [
    { id: "edge:script-call:workflow%3Aorch-spec:script%3Abin%2Ftickets.py", kind: "script-call", from: "workflow:orch-spec", to: "script:bin/tickets.py", label: "calls script" },
    { id: "edge:skill-call:workflow%3Aorch-spec:skill%3Aorch-decompose", kind: "skill-call", from: "workflow:orch-spec", to: "skill:orch-decompose", label: "calls skill" },
    { id: "edge:skill-call:workflow%3Aorch-spec:skill%3Aorch-frontier", kind: "skill-call", from: "workflow:orch-spec", to: "skill:orch-frontier", label: "calls skill" },
    { id: "edge:skill-call:workflow%3Aorch-spec:skill%3Aorch-integrate", kind: "skill-call", from: "workflow:orch-spec", to: "skill:orch-integrate", label: "calls skill" },
    { id: "edge:skill-call:workflow%3Aorch-spec:skill%3Aorch-investigate", kind: "skill-call", from: "workflow:orch-spec", to: "skill:orch-investigate", label: "calls skill" },
  ],
  relations: [
    { id: "edge:script-call:workflow%3Aorch-spec:script%3Abin%2Ftickets.py", kind: "script-call", from: "workflow:orch-spec", to: "script:bin/tickets.py", label: "calls script" },
    { id: "edge:skill-call:workflow%3Aorch-spec:skill%3Aorch-decompose", kind: "skill-call", from: "workflow:orch-spec", to: "skill:orch-decompose", label: "calls skill" },
    { id: "edge:skill-call:workflow%3Aorch-spec:skill%3Aorch-frontier", kind: "skill-call", from: "workflow:orch-spec", to: "skill:orch-frontier", label: "calls skill" },
    { id: "edge:skill-call:workflow%3Aorch-spec:skill%3Aorch-integrate", kind: "skill-call", from: "workflow:orch-spec", to: "skill:orch-integrate", label: "calls skill" },
    { id: "edge:skill-call:workflow%3Aorch-spec:skill%3Aorch-investigate", kind: "skill-call", from: "workflow:orch-spec", to: "skill:orch-investigate", label: "calls skill" },
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
