import type { InspectorRoute } from "./route";

export type ReadinessState = "waiting" | "ready" | "running" | "attention" | "complete" | "unknown";
export type ReadinessCause = "pending_dependency" | "suspended_handoff" | "failed_upstream" | "blocked_upstream" | "stale_claim" | "malformed_topology" | "none";

export interface TicketSummary {
  id: string;
  status: string;
  executor: string;
  bound: string;
  claimed_at: string;
  claimed_by: string;
  depends_on: string[];
  unreadable: boolean;
  readiness: {
    state: ReadinessState;
    dependencies: string[];
    explanation: string;
    cause: ReadinessCause;
    causal_chain: string[];
  };
}

export interface TicketDetail extends TicketSummary {
  sections: Record<string, string>;
  report: string;
  pack: string;
  history: Array<{ ts: string; event: string; agent: string; detail: string }>;
  raw: string;
  linked_friction?: Array<Record<string, unknown>>;
  executor_source?: ExecutorSource;
  artifacts?: ArtifactInventory;
}

export interface ExecutorSource {
  state: "available" | "unavailable";
  workflow_id?: string;
  source_id?: string;
  label?: string;
  reason?: string;
}

export interface ArtifactReference {
  artifact_id: string;
  label: string;
  state: "available" | "unavailable";
  media_type?: string;
  reason?: string;
}

export interface ArtifactInventory {
  state: "rows" | "unavailable";
  rows: ArtifactReference[];
  reason?: string;
}

export interface InspectorModel {
  run: Record<string, unknown> | null;
  ticket: TicketDetail | null;
}

export const inspectorTabs = ["overview", "details", "report", "artifacts", "friction", "history", "raw"] as const;
export type InspectorTab = (typeof inspectorTabs)[number];
export type InspectorState = ReadinessState | "failed";

// The section names the sink still holds from the earlier executor grammar.
// History is never rewritten, so a ticket filed under the five-section
// contract keeps them; the browser shows each one as recorded.
export const historicalSections = ["result", "verification", "feedback", "risks", "handoff"] as const;

export interface ReportBlock {
  name: string;
  body: string;
  historical: boolean;
}

export interface InspectorFrictionRecord {
  ts: string;
  observed: string;
  expected: string;
  host: string;
}

export interface InspectorHistoryRecord {
  ts: string;
  event: string;
  agent: string;
  detail: string;
}

export interface InspectorArtifact {
  id: string;
  label: string;
  mediaType: string;
  href: string | null;
  reason: string;
}

export interface InspectorExecutorSource {
  label: string;
  href: string | null;
  reason: string;
}

type UnknownRecord = Record<string, unknown>;

const fixtureTab: Record<string, InspectorTab> = {
  "running-overview": "overview",
  "report-recorded": "report",
  "report-historical": "report",
  "friction-present": "friction",
  "history-unavailable": "history",
  "raw-escaped": "raw"
};

const fixtureRaw = `---
id: A2
run: run-alpha
status: claimed
executor: orch-execute
depends_on:
  - A1
write_scope:
  - scratch/a2.txt
bound: 45m
claimed_by: fixture-agent
claimed_at: 2026-01-01T00:05:00Z
---

## Goal

Untrusted ticket text: <script>alert(1)</script> must reach the page as
escaped characters, never as live markup.

## Report

Nothing was done; this file exists to be read.`;

const fixtureReport = [
  "Gate replayed at the tip: validate, tests, the serial lane, the dry run and the whitespace check all exited 0.",
  "Kept the projection privacy wall unchanged. The report body is the one executor filing; it is shown exactly as recorded and nothing parses it."
].join("\n\n");

const fixtureHistoricalSections = {
  result: "The recorded result under the earlier grammar.",
  verification: [
    "| # | verdict | oracle | class | evidence |",
    "| --- | --- | --- | --- | --- |",
    "| 1 | PASS | tools/validate.py | deterministic | exit 0, zero output |",
    "| 2 | FAIL | install.py --dry-run | deterministic | plan named 3 scripts, 4 expected |"
  ].join("\n"),
  feedback: "[]",
  risks: "[]"
};

export function fixtureTicket(location: InspectorRoute): TicketDetail | null {
  if (!fixtureTab[location.fixture]) return null;
  const running = location.fixture === "running-overview";
  const unavailableHistory = location.fixture === "history-unavailable";
  const raw = location.fixture === "raw-escaped";
  const recorded = location.fixture === "report-recorded";
  const historical = location.fixture === "report-historical";
  return {
    id: location.ticket,
    status: running || raw ? "claimed" : unavailableHistory ? "suspended" : historical ? "failed" : "complete",
    executor: running ? "orch-render" : raw ? "orch-execute" : "orch-tdd",
    bound: running ? "90m" : unavailableHistory ? "30m" : raw ? "45m" : "90m",
    claimed_at: "2026-01-01T00:20:00Z",
    claimed_by: "fixture-agent",
    depends_on: raw ? ["A1"] : [],
    unreadable: false,
    readiness: {
      state: running || raw ? "running" : unavailableHistory || historical ? "attention" : "complete",
      dependencies: [],
      explanation: running
        ? "The assigned worker is executing this ticket within its bound."
        : raw
          ? "The worker holds the claim; only the inert ticket source is projected."
          : unavailableHistory
            ? "The ticket is suspended and has no durable event projection."
            : historical
              ? "This ticket failed under the earlier section grammar; its recorded sections are shown as written."
              : "Every dependency is met and the report is recorded.",
      cause: unavailableHistory ? "suspended_handoff" : "none",
      causal_chain: []
    },
    sections: {
      goal: raw
        ? "Untrusted ticket text: <script>alert(1)</script> must remain inert."
        : running
          ? "Expose canonical ticket evidence without revealing private agent activity."
          : "Keep the executor's one report legible without parsing anything out of it.",
      ...(historical ? fixtureHistoricalSections : {})
    },
    report: recorded ? fixtureReport : "",
    pack: "orch-design-pack",
    history: [],
    raw: raw ? fixtureRaw : ""
  };
}

function record(value: unknown): UnknownRecord {
  return value && typeof value === "object" ? value as UnknownRecord : {};
}

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export function selectedTab(location: InspectorRoute, search = window.location.search): InspectorTab {
  const requested = new URLSearchParams(search).get("tab")?.toLowerCase();
  if (inspectorTabs.includes(requested as InspectorTab)) return requested as InspectorTab;
  return fixtureTab[location.fixture] ?? "overview";
}

export function tabPath(tab: InspectorTab, search = window.location.search): string {
  const query = new URLSearchParams(search);
  query.set("tab", tab);
  return `${window.location.pathname}?${query.toString()}`;
}

export function statusState(ticket: TicketSummary): InspectorState {
  if (ticket.status === "failed") return "failed";
  if (ticket.readiness.state !== "unknown") return ticket.readiness.state;
  if (ticket.status === "claimed") return "running";
  if (ticket.status === "ready") return "ready";
  if (ticket.status === "complete") return "complete";
  if (["blocked", "suspended", "failed"].includes(ticket.status)) return "attention";
  if (ticket.status === "pending") return "waiting";
  return "unknown";
}

export function detailRows(ticket: TicketDetail | null): Array<{ label: string; value: string; mono?: boolean }> {
  if (!ticket) return [];
  return [
    { label: "Worker", value: ticket.executor || "Unavailable", mono: true },
    { label: "Dependencies", value: ticket.depends_on.length ? ticket.depends_on.join(", ") : "None", mono: true },
    { label: "Limit", value: ticket.bound || "Unavailable" },
    { label: "Claim", value: ticket.claimed_by && ticket.claimed_at ? `${ticket.claimed_by} · ${ticket.claimed_at}` : "Unclaimed" },
    { label: "Pack", value: ticket.pack || "Unavailable", mono: true }
  ];
}

export function executorSource(ticket: TicketDetail): InspectorExecutorSource {
  const source = ticket.executor_source;
  if (source?.state === "available" && source.workflow_id && source.source_id) {
    return {
      label: source.label || ticket.executor,
      href: `/workflows/${encodeURIComponent(source.workflow_id)}/sources/${encodeURIComponent(source.source_id)}`,
      reason: ""
    };
  }
  return {
    label: ticket.executor,
    href: null,
    reason: source?.reason || "No canonical workflow association was recorded."
  };
}

function opaqueArtifactId(value: string): boolean {
  return /^[A-Za-z0-9_-]{16,128}$/.test(value);
}

export function artifactRows(ticket: TicketDetail, location: InspectorRoute): InspectorArtifact[] {
  return (ticket.artifacts?.rows ?? []).map((item) => {
    const contained = item.state === "available" && opaqueArtifactId(item.artifact_id);
    return {
      id: item.artifact_id,
      label: item.label || "Unnamed artifact",
      mediaType: item.media_type || "Media type unavailable",
      href: contained
        ? `/api/v1/runs/${encodeURIComponent(location.run)}/tickets/${encodeURIComponent(location.ticket)}/artifacts/${encodeURIComponent(item.artifact_id)}`
        : null,
      reason: contained ? "" : item.reason || "Artifact identity unavailable"
    };
  });
}

export function reportBlocks(ticket: TicketDetail | null): ReportBlock[] {
  if (!ticket) return [];
  if (ticket.report.trim()) return [{ name: "Report", body: ticket.report, historical: false }];
  return historicalSections
    .filter((name) => (ticket.sections[name] ?? "").trim())
    .map((name) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1),
      body: ticket.sections[name],
      historical: true
    }));
}

export function linkedFriction(model: InspectorModel, location: InspectorRoute): InspectorFrictionRecord[] {
  const rows = model.ticket?.linked_friction ?? [];
  const linked = rows.map(record).filter((item) =>
    text(item.run) === location.run && text(item.ticket) === location.ticket
  );
  if (!linked.length && location.fixture === "friction-present") {
    linked.push({
      run: location.run,
      ticket: location.ticket,
      ts: "2026-08-03T11:00:00Z",
      observed: "A deterministic oracle returned a failing verdict.",
      expected: "Every named criterion to carry verified evidence.",
      host: "fixture"
    });
  }
  return linked.map((item) => ({
    ts: text(item.ts) || "Timestamp unavailable",
    observed: text(item.observed) || "Observation unavailable",
    expected: text(item.expected) || "Expectation unavailable",
    host: text(item.host) || "Host unavailable"
  }));
}

export function durableHistory(model: InspectorModel, location: InspectorRoute): InspectorHistoryRecord[] {
  if (location.fixture === "history-unavailable") return [];
  return (model.ticket?.history ?? []).map((item) => ({
    ts: item.ts || "Timestamp unavailable",
    event: item.event || "unknown event",
    agent: item.agent || "Agent unavailable",
    detail: item.detail
  }));
}

export function redactHostPaths(value: string): string {
  return value
    .replace(/[A-Za-z]:\\(?:Users|Documents and Settings)\\[^\s\\]+(?:\\[^\s]*)?/g, "[redacted-path]")
    .replace(/\/(?:Users|home)\/[^\s/]+(?:\/[^\s]*)?/g, "[redacted-path]");
}

export function rawTicket(model: InspectorModel, location: InspectorRoute): string {
  const projected = model.ticket?.raw ?? "";
  if (projected) return redactHostPaths(projected);
  if (location.fixture === "raw-escaped") return fixtureRaw;
  return "Raw ticket markdown is unavailable in this reader projection.";
}

export const model = {
  selectedTab,
  tabPath,
  statusState,
  detailRows,
  executorSource,
  artifactRows,
  reportBlocks,
  linkedFriction,
  durableHistory,
  rawTicket,
};
