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
  verification: { state: string; rows: Array<Record<string, string>> };
  inputs: string[];
  write_scope: string[];
  pack: string;
  history: Array<{ ts: string; event: string; agent: string; detail: string }>;
  raw: string;
  linked_friction?: Array<Record<string, unknown>>;
  executor_source?: ExecutorSource;
  artifacts?: ArtifactInventory;
  judgment?: JudgmentProjection;
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

export interface RationaleIdentity {
  kind: string;
  id: string;
}

export interface JudgmentProjection {
  rationale: {
    state: "available" | "unavailable";
    identity: RationaleIdentity | null;
  };
}

export interface InspectorModel {
  run: Record<string, unknown> | null;
  ticket: TicketDetail | null;
}

export const inspectorTabs = ["overview", "details", "proof", "artifacts", "friction", "history", "raw"] as const;
export type InspectorTab = (typeof inspectorTabs)[number];
export type InspectorState = ReadinessState | "failed";

export interface InspectorProofRow {
  criterion: string;
  verdict: string;
  oracle: string;
  oracleClass: string;
  evidence: string;
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
  "proof-pass": "proof",
  "proof-fail": "proof",
  "friction-present": "friction",
  "history-unavailable": "history",
  "raw-escaped": "raw"
};

const fixtureRaw = `---
id: A2
run: run-alpha
status: claimed
executor: orch-verify
depends_on:
  - A1
write_scope:
  - scratch/a2.txt
bound: 45m
claimed_by: fixture-agent
claimed_at: 2026-01-01T00:05:00Z
---

## Objective

Untrusted ticket text: <script>alert(1)</script> must reach the page as
escaped characters, never as live markup.

## Result

Nothing was done; this file exists to be read.`;

const proofFixtureRows = [
  { "#": "1", verdict: "PASS", oracle: "tools/validate.py", class: "deterministic", evidence: "exit 0, zero output" },
  { "#": "2", verdict: "PASS", oracle: "the named test", class: "deterministic", evidence: "(?:src|href) matched nothing on either route" },
  { "#": "3", verdict: "PASS", oracle: "install.py --dry-run", class: "deterministic", evidence: "plan named 4 scripts, 4 expected" }
];

export function fixtureTicket(location: InspectorRoute): TicketDetail | null {
  if (!fixtureTab[location.fixture]) return null;
  const running = location.fixture === "running-overview";
  const unavailableHistory = location.fixture === "history-unavailable";
  const raw = location.fixture === "raw-escaped";
  const proof = location.fixture.startsWith("proof-");
  const failing = location.fixture === "proof-fail";
  const rows = proof ? proofFixtureRows.map((row, index) =>
    location.fixture === "proof-fail" && index === 2
      ? { ...row, verdict: "FAIL", evidence: "plan named 3 scripts, 4 expected" }
      : row
  ) : [];
  return {
    id: location.ticket,
    status: running || raw ? "claimed" : unavailableHistory ? "suspended" : location.fixture === "proof-fail" ? "failed" : "complete",
    executor: running ? "orch-render" : raw ? "orch-verify" : "orch-tdd",
    bound: running ? "90m" : unavailableHistory ? "30m" : raw ? "45m" : "90m",
    claimed_at: "2026-01-01T00:20:00Z",
    claimed_by: "fixture-agent",
    depends_on: raw ? ["A1"] : [],
    unreadable: false,
    readiness: {
      state: running || raw ? "running" : unavailableHistory || failing ? "attention" : "complete",
      dependencies: [],
      explanation: running
        ? "The assigned worker is executing this ticket within its bound."
        : raw
          ? "The worker holds the claim; only the inert ticket source is projected."
          : unavailableHistory
            ? "The ticket is suspended and has no durable event projection."
            : failing
              ? "One named criterion returned a failing verdict."
              : "Every dependency and criterion is complete.",
      cause: unavailableHistory ? "suspended_handoff" : "none",
      causal_chain: []
    },
    sections: {
      objective: raw
        ? "Untrusted ticket text: <script>alert(1)</script> must remain inert."
        : running
          ? "Expose canonical ticket evidence without revealing private agent activity."
          : "Keep each verification criterion, oracle, verdict, and evidence identity visible.",
      ...(proof ? { result: location.fixture === "proof-pass" ? "All criteria passed." : "One criterion requires attention." } : {})
    },
    verification: { state: rows.length ? "rows" : "unknown", rows },
    inputs: ["accepted reader projection", "frozen view identity"],
    write_scope: ["web/src/features/inspector"],
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
    { label: "Inputs", value: ticket.inputs.length ? ticket.inputs.join(", ") : "Unavailable" },
    { label: "Scope", value: ticket.write_scope.length ? ticket.write_scope.join(", ") : "Unavailable", mono: true },
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

export function proofRows(model: InspectorModel, fixture: string): InspectorProofRow[] {
  const rows = model.ticket?.verification.rows ?? [];
  return rows.map((value, index) => {
    const row = record(value);
    const verdict = text(row.verdict) || "UNKNOWN";
    return {
      criterion: text(row["#"]) || String(index + 1),
      verdict,
      oracle: text(row.oracle) || "Unavailable",
      oracleClass: text(row.class) || "unknown",
      evidence: text(row.evidence) || "No evidence identity recorded"
    };
  });
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
  proofRows,
  linkedFriction,
  durableHistory,
  rawTicket,
};
