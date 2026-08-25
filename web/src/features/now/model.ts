import type { WorkflowSummary } from "../workflows/view/SummaryFlow";

export type ReadinessState = "waiting" | "ready" | "running" | "attention" | "complete" | "unknown";
export type ReadinessCause = "pending_dependency" | "suspended_handoff" | "failed_upstream" | "blocked_upstream" | "stale_claim" | "malformed_topology" | "none";

export interface Readiness {
  state: ReadinessState;
  dependencies: string[];
  explanation: string;
  cause: ReadinessCause;
  causal_chain: string[];
}

export interface NowTicket {
  id: string;
  status: string;
  executor: string;
  bound: string;
  claimed_at: string;
  claimed_by: string;
  depends_on: string[];
  readiness: Readiness;
  unreadable: boolean;
  title?: string;
  required?: boolean;
}

export interface NowRunPayload {
  id: string;
  ticket_count: number;
  active: boolean;
  objective: string;
  repository: string;
  client: string;
  last_activity: string;
  terminal_at?: string;
  terminal_status?: string;
  unreadable: boolean;
  tickets: NowTicket[];
}

export type NowBand = "attention" | "active" | "completed";
export type GroupState = ReadinessState;

export interface NowRun {
  id: string;
  objective: string;
  /** Recorded project leaf name; the empty string when the run never recorded one. */
  repository: string;
  client?: string;
  lastActivity: string;
  /** Verbatim run.json terminal timing; empty while the run is live. */
  terminalAt?: string;
  terminalStatus?: string;
  tickets: NowTicket[];
  unreadable?: boolean;
}

export interface NowModel {
  runs: NowRun[];
}

export interface NowGroup {
  id: string;
  label: string;
  state: GroupState;
  ticketIds: string[];
  edges: Array<{ source: string; target: string }>;
  counts: Record<string, number>;
}

export interface FleetRun extends NowRun {
  band: NowBand;
  groups: NowGroup[];
  path: string;
  counts: Record<string, number>;
}

export interface NowWork {
  current: NowTicket[];
  next: NowTicket[];
  unknown: NowTicket[];
}

const ATTENTION = new Set(["failed", "blocked", "stalled", "limited", "suspended"]);

export function projectWork(tickets: NowTicket[]): NowWork {
  const unknown = tickets.filter((ticket) => ticket.unreadable || ticket.readiness.state === "unknown");
  const known = tickets.filter((ticket) => !unknown.includes(ticket));
  return {
    current: known.filter((ticket) => ATTENTION.has(ticket.status)
      || ticket.status === "claimed"
      || ticket.readiness.state === "attention"
      || ticket.readiness.state === "running"),
    next: known.filter((ticket) => ticket.status === "ready" || ticket.readiness.state === "ready"),
    unknown,
  };
}

function countsFor(tickets: NowTicket[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const ticket of tickets) counts[ticket.status] = (counts[ticket.status] ?? 0) + 1;
  return counts;
}

export function groupState(tickets: NowTicket[]): GroupState {
  if (!tickets.length || tickets.some((ticket) => ticket.unreadable)) return "unknown";
  if (tickets.some((ticket) => ATTENTION.has(ticket.status) || ticket.readiness.state === "attention")) return "attention";
  if (tickets.some((ticket) => ticket.status === "claimed" || ticket.readiness.state === "running")) return "running";
  if (tickets.some((ticket) => ticket.status === "ready" || ticket.readiness.state === "ready")) return "ready";
  if (tickets.every((ticket) => ticket.required === false || ticket.status === "complete")) return "complete";
  if (tickets.some((ticket) => ticket.status !== "complete")) return "waiting";
  return "unknown";
}

/** Canonical dependency depth; malformed references stay in an explicit unknown layer. */
export function dependencyLayers(tickets: NowTicket[]): string[][] {
  const byId = new Map(tickets.map((ticket) => [ticket.id, ticket]));
  const depths = new Map<string, number>();
  const visiting = new Set<string>();
  const malformed = new Set<string>();

  const visit = (id: string): number => {
    if (depths.has(id)) return depths.get(id)!;
    if (visiting.has(id)) {
      malformed.add(id);
      return -1;
    }
    visiting.add(id);
    const ticket = byId.get(id)!;
    let depth = 0;
    for (const dependency of ticket.depends_on) {
      if (!byId.has(dependency)) {
        malformed.add(id);
        continue;
      }
      const parentDepth = visit(dependency);
      if (parentDepth < 0) malformed.add(id);
      else depth = Math.max(depth, parentDepth + 1);
    }
    visiting.delete(id);
    depths.set(id, malformed.has(id) ? -1 : depth);
    return depths.get(id)!;
  };

  for (const ticket of tickets) visit(ticket.id);
  const maximum = Math.max(0, ...depths.values());
  const layers = Array.from({ length: maximum + 1 }, () => [] as string[]);
  const unknown: string[] = [];
  for (const ticket of tickets) {
    const depth = depths.get(ticket.id) ?? -1;
    (depth < 0 ? unknown : layers[depth]).push(ticket.id);
  }
  const populated = layers.filter((layer) => layer.length);
  if (unknown.length) populated.push(unknown);
  return populated;
}

function layerLabel(index: number, total: number): string {
  if (index === 0) return "Brief";
  if (index === 1 && total > 2) return "Plan";
  if (index === total - 1 && total > 3) return "Verify";
  if (index === total - 2 && total > 4) return "Review";
  return "Work";
}

export function projectGroups(tickets: NowTicket[]): NowGroup[] {
  const byId = new Map(tickets.map((ticket) => [ticket.id, ticket]));
  const layers = dependencyLayers(tickets);
  const buckets: Array<{ label: string; ids: string[] }> = [];
  layers.forEach((ids, index) => {
    const malformed = ids.some((id) => byId.get(id)?.unreadable || byId.get(id)?.depends_on.some((dep) => !byId.has(dep)));
    const label = malformed ? "Unknown" : layerLabel(index, layers.length);
    const previous = buckets.at(-1);
    if (previous?.label === label) previous.ids.push(...ids);
    else buckets.push({ label, ids: [...ids] });
  });
  return buckets.map((bucket, index) => {
    const members = bucket.ids.map((id) => byId.get(id)!).filter(Boolean);
    const memberIds = new Set(bucket.ids);
    const edges = members.flatMap((ticket) => ticket.depends_on
      .filter((source) => memberIds.has(source))
      .map((source) => ({ source, target: ticket.id })));
    return {
      id: `${index}-${bucket.label.toLowerCase()}`,
      label: bucket.label,
      state: groupState(members),
      ticketIds: bucket.ids,
      edges,
      counts: countsFor(members),
    };
  });
}

function runBand(groups: NowGroup[]): NowBand {
  if (groups.some((group) => group.state === "attention" || group.state === "unknown")) return "attention";
  if (groups.length && groups.every((group) => group.state === "complete")) return "completed";
  return "active";
}

export function projectFleet(runs: NowRun[]): FleetRun[] {
  const seen = new Set<string>();
  return runs.flatMap((run) => {
    if (seen.has(run.id)) return [];
    seen.add(run.id);
    const groups = projectGroups(run.tickets);
    const names = groups.map((group) => group.label === "Work" && group.ticketIds.length > 1
      ? `Work x${group.ticketIds.length}` : group.label);
    return [{ ...run, groups, band: runBand(groups), path: names.join(" → "), counts: countsFor(run.tickets) }];
  }).sort((left, right) => {
    const order: Record<NowBand, number> = { attention: 0, active: 1, completed: 2 };
    return order[left.band] - order[right.band] || left.id.localeCompare(right.id);
  });
}

export const bandLabel: Record<NowBand, string> = {
  attention: "Needs attention",
  active: "Active now",
  completed: "Recently completed",
};

export const UNRECORDED_FOLDER = "Folder unrecorded";

export interface NowFolder {
  key: string;
  label: string;
  runs: FleetRun[];
  /** Newest terminal_at held by a member run; the empty string when none recorded one. */
  newestTerminal: string;
  attention: boolean;
}

export interface NowFolders {
  running: NowFolder[];
  past: NowFolder[];
}

/** A finished run is one the record says finished; a live run never carries terminal timing. */
export function isPast(run: FleetRun): boolean {
  return Boolean(run.terminalAt) || run.band === "completed";
}

export function folderLabel(run: NowRun): string {
  return run.repository.trim() || UNRECORDED_FOLDER;
}

function collect(runs: FleetRun[]): NowFolder[] {
  const folders = new Map<string, NowFolder>();
  for (const run of runs) {
    const label = folderLabel(run);
    const folder = folders.get(label)
      ?? { key: label, label, runs: [], newestTerminal: "", attention: false };
    folder.runs.push(run);
    folder.attention = folder.attention || run.band === "attention";
    if ((run.terminalAt ?? "") > folder.newestTerminal) folder.newestTerminal = run.terminalAt ?? "";
    folders.set(label, folder);
  }
  return [...folders.values()];
}

/**
 * Group the fleet by its recorded folder leaf: running folders first with trouble
 * on top, finished folders ordered by their newest recorded terminal_at.
 */
export function projectFolders(fleet: FleetRun[]): NowFolders {
  const running = collect(fleet.filter((run) => !isPast(run)))
    .sort((left, right) => Number(right.attention) - Number(left.attention)
      || left.label.localeCompare(right.label));
  const past = collect(fleet.filter(isPast))
    .map((folder) => ({
      ...folder,
      runs: [...folder.runs].sort((left, right) => (right.terminalAt ?? "").localeCompare(left.terminalAt ?? "")
        || left.id.localeCompare(right.id)),
    }))
    .sort((left, right) => right.newestTerminal.localeCompare(left.newestTerminal)
      || left.label.localeCompare(right.label));
  return { running, past };
}

/** The run's group chain as the shared summary flow reads it, with each group's exact state. */
export function runSummary(run: FleetRun): { summary: WorkflowSummary; nodeStates: Record<string, string> } {
  const nodes = run.groups.map((group) => ({
    id: group.id,
    label: group.ticketIds.length > 1 ? `${group.label} ×${group.ticketIds.length}` : group.label,
  }));
  const edges = run.groups.slice(1).map((group, index) => ({
    source: run.groups[index].id,
    target: group.id,
    kind: "sequence" as const,
  }));
  const nodeStates: Record<string, string> = {};
  for (const group of run.groups) nodeStates[group.id] = group.state;
  return { summary: { nodes, edges }, nodeStates };
}

export const model = {
  dependencyLayers, groupState, projectGroups, projectFleet, projectWork, projectFolders,
  runSummary, folderLabel, isPast, bandLabel,
};
