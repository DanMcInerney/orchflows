import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
  type NodeProps
} from "@xyflow/react";
import {
  AlertTriangle,
  Box,
  ChevronLeft,
  ChevronRight,
  CircleDot,
  Focus,
  GitBranch,
  LockKeyhole,
  Maximize2,
  Pause,
  Play,
  Search,
  ShieldAlert,
  X
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { RunDetail, TicketSummary } from "../../api/schema";
import type { ViewProps } from "../../app/registry";
import { runForIdentity } from "./fixtures";
import {
  authoritativeCausalFocus,
  buildTopology,
  filterTickets,
  readinessGroups,
  type CausalFocus,
  type ReadinessGroup,
  type RunMapFilter
} from "./model";
import "./run-map.css";

type DisclosureLevel = 0 | 1 | 2 | 3;

interface TicketNodeData extends Record<string, unknown> {
  ticket: TicketSummary;
  causal: "focus" | "dimmed" | "off";
}

interface GroupNodeData extends Record<string, unknown> {
  group: ReadinessGroup;
}

const FILTERS: Array<{ id: RunMapFilter; label: string }> = [
  { id: "active", label: "Active" },
  { id: "problems", label: "Problems" },
  { id: "ready", label: "Ready now" },
  { id: "critical", label: "Critical path" },
  { id: "all", label: "All" }
];

function initialLevel(identity: string): DisclosureLevel {
  if (identity === "summary-active" || identity === "completed") return 1;
  if (identity === "blocked-causal") return 3;
  return 2;
}

function statusGlyph(state: string): string {
  if (state === "complete") return "✓";
  if (state === "attention") return "!";
  if (state === "running") return "◉";
  if (state === "ready") return "▶";
  if (state === "waiting") return "•";
  return "?";
}

function TicketNode({ data, selected }: NodeProps) {
  const { ticket, causal } = data as TicketNodeData;
  return (
    <article
      className="run-ticket-node"
      data-status={ticket.readiness.state}
      data-causal={causal}
      aria-label={`${ticket.id}, ${ticket.readiness.state}: ${ticket.readiness.explanation}`}
      aria-current={selected ? "true" : undefined}
    >
      <span className="run-ticket-node__glyph" aria-hidden="true">{statusGlyph(ticket.readiness.state)}</span>
      <strong>{ticket.id}</strong>
      <span className="run-ticket-node__state">{ticket.readiness.state}</span>
      <small>{ticket.executor || "executor unavailable"}</small>
    </article>
  );
}

function GroupNode({ data, selected }: NodeProps) {
  const { group } = data as GroupNodeData;
  return (
    <article className="run-group-node" data-status={group.id} aria-current={selected ? "true" : undefined}>
      <span className="run-group-node__glyph" aria-hidden="true">{statusGlyph(group.id)}</span>
      <div><strong>{group.label}</strong><small>{group.ticketIds.length} work items</small></div>
      <span className="run-group-node__ids">{group.ticketIds.join(" · ")}</span>
    </article>
  );
}

const nodeTypes = { ticket: TicketNode, group: GroupNode };

function projectedGraph(
  tickets: TicketSummary[],
  expanded: boolean,
  selectedTicket: string,
  selectedGroup: string,
  causal: CausalFocus | null
): { nodes: Node[]; edges: Edge[] } {
  const topology = buildTopology(tickets);
  const focus = new Set(causal?.ticketIds ?? []);
  if (expanded) {
    const nodes: Node[] = tickets.map((ticket, index) => ({
      id: ticket.id,
      type: "ticket",
      position: { x: 56 + (index % 3) * 264, y: 56 + Math.floor(index / 3) * 140 },
      selected: ticket.id === selectedTicket,
      data: {
        ticket,
        causal: causal ? (focus.has(ticket.id) ? "focus" : "dimmed") : "off"
      } satisfies TicketNodeData
    }));
    const missing = [...new Set(topology.edges.filter((edge) => edge.missingSource).map((edge) => edge.source))];
    for (const [index, id] of missing.entries()) nodes.push({
      id,
      type: "ticket",
      position: { x: 56 + ((tickets.length + index) % 3) * 264, y: 56 + Math.floor((tickets.length + index) / 3) * 140 },
      data: {
        ticket: {
          id,
          status: "missing",
          executor: "",
          bound: "",
          claimed_at: "",
          claimed_by: "",
          depends_on: [],
          unreadable: true,
          readiness: { state: "unknown", dependencies: [], explanation: `${id} is a missing dependency` }
        },
        causal: causal ? (focus.has(id) ? "focus" : "dimmed") : "off"
      } satisfies TicketNodeData
    });
    return {
      nodes,
      edges: topology.edges.map((edge) => {
        const causalId = `${edge.source}->${edge.target}`;
        const isFocus = Boolean(causal?.edgeIds.includes(causalId));
        return {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          focusable: true,
          ariaLabel: `${edge.source} is a dependency of ${edge.target}`,
          className: causal ? (isFocus ? "run-edge--focus" : "run-edge--dimmed") : "",
          animated: false
        };
      })
    };
  }

  const groups = readinessGroups(tickets);
  const byTicket = new Map(groups.flatMap((group) => group.ticketIds.map((id) => [id, group.id])));
  const bundles = new Map<string, { source: string; target: string; count: number }>();
  for (const edge of topology.edges) {
    const source = byTicket.get(edge.source);
    const target = byTicket.get(edge.target);
    if (!source || !target || source === target) continue;
    const id = `${source}->${target}`;
    const bundle = bundles.get(id) ?? { source, target, count: 0 };
    bundle.count += 1;
    bundles.set(id, bundle);
  }
  return {
    nodes: groups.map((group, index) => ({
      id: `group:${group.id}`,
      type: "group",
      position: { x: 64 + (index % 2) * 352, y: 68 + Math.floor(index / 2) * 156 },
      selected: group.id === selectedGroup,
      data: { group } satisfies GroupNodeData
    })),
    edges: [...bundles.entries()].map(([id, bundle]) => ({
      id,
      source: `group:${bundle.source}`,
      target: `group:${bundle.target}`,
      label: `${bundle.count}`,
      focusable: true,
      ariaLabel: `${bundle.count} dependencies from ${bundle.source} to ${bundle.target}`
    }))
  };
}

function FleetView({ runs, currentRun, onOpen }: {
  runs: ViewProps["snapshot"]["runs"];
  currentRun: string;
  onOpen: () => void;
}) {
  return (
    <section className="run-fleet" aria-labelledby="fleet-heading">
      <header><p className="run-map__eyebrow">Level 0 · fleet</p><h2 id="fleet-heading">Current workflows</h2></header>
      <div className="run-fleet__list">
        {runs.map((run) => (
          <button key={run.id} type="button" className="run-fleet__row" onClick={run.id === currentRun ? onOpen : undefined}>
            <span className="run-fleet__identity"><CircleDot aria-hidden="true" /><strong>{run.id}</strong></span>
            <span className="run-fleet__macro" aria-label={`${run.ticket_count} work items`}>
              {Array.from({ length: Math.min(run.ticket_count, 6) }, (_, index) => <i key={index} />)}
            </span>
            <span className={`run-fleet__state ${run.active ? "is-active" : ""}`}>{run.active ? "active" : "settled"}</span>
            <ChevronRight aria-hidden="true" />
          </button>
        ))}
      </div>
    </section>
  );
}

function SummaryView({ run, onGroup, onExpand }: {
  run: RunDetail;
  onGroup: (group: ReadinessGroup) => void;
  onExpand: () => void;
}) {
  const groups = readinessGroups(run.tickets);
  return (
    <section className="run-summary" aria-labelledby="summary-heading">
      <header className="run-summary__heading">
        <div><p className="run-map__eyebrow">Level 1 · grouped summary</p><h2 id="summary-heading">Readiness, without invented phases</h2></div>
        <button type="button" className="run-map__primary" onClick={onExpand}><GitBranch aria-hidden="true" />Open canonical graph</button>
      </header>
      <div className="run-summary__groups">
        {groups.map((group) => (
          <button key={group.id} type="button" className="run-summary__group" data-status={group.id} onClick={() => onGroup(group)}>
            <span className="run-summary__glyph" aria-hidden="true">{statusGlyph(group.id)}</span>
            <span><strong>{group.label}</strong><small>{group.statuses.join(" / ")} · {group.ticketIds.join(", ")}</small></span>
            <b>{group.ticketIds.length}</b><ChevronRight aria-hidden="true" />
          </button>
        ))}
      </div>
    </section>
  );
}

function Inspector({ ticket, group, causal, onWhy, onClose }: {
  ticket: TicketSummary | null;
  group: ReadinessGroup | null;
  causal: CausalFocus | null;
  onWhy: () => void;
  onClose: () => void;
}) {
  return (
    <aside className="run-inspector" aria-labelledby="inspector-heading">
      <header>
        <div><p className="run-map__eyebrow">Level 3 · inspector</p><h2 id="inspector-heading">{ticket?.id ?? group?.label ?? "Selection"}</h2></div>
        <button type="button" className="run-map__icon" onClick={onClose} aria-label="Close inspector"><X aria-hidden="true" /></button>
      </header>
      {ticket && <>
        <div className="run-inspector__status" data-status={ticket.readiness.state}>
          <span aria-hidden="true">{statusGlyph(ticket.readiness.state)}</span>
          <strong>{ticket.readiness.state}</strong><small>canonical status: {ticket.status}</small>
        </div>
        {ticket.readiness.dependencies.length > 0 && (
          <button type="button" className="run-map__why" aria-pressed={Boolean(causal)} onClick={onWhy}>
            <Focus aria-hidden="true" />Why waiting?
          </button>
        )}
        {causal && <div className="run-inspector__cause" role="status" data-cause={causal.kind}>
          <ShieldAlert aria-hidden="true" /><div><strong>{causal.summary}</strong><p>{causal.evidence}</p><code>{causal.ticketIds.join(" ← ")}</code></div>
        </div>}
        <dl>
          <div><dt>Executor</dt><dd>{ticket.executor || "unavailable"}</dd></div>
          <div><dt>Depends on</dt><dd>{ticket.depends_on.join(", ") || "none"}</dd></div>
          <div><dt>Bound</dt><dd>{ticket.bound || "unavailable"}</dd></div>
          <div><dt>Claim</dt><dd>{ticket.claimed_by || "unclaimed"}</dd></div>
        </dl>
        <p className="run-inspector__evidence">{ticket.readiness.explanation}</p>
      </>}
      {group && <div className="run-inspector__group">
        <p>This summary is a reversible projection of canonical readiness.</p>
        <strong>{group.ticketIds.join(", ")}</strong>
        <small>Statuses: {group.statuses.join(", ")}</small>
      </div>}
      <p className="run-inspector__privacy"><LockKeyhole aria-hidden="true" />Only closed ticket metadata is shown. Prompts, tools, files, output, and conversations stay private.</p>
    </aside>
  );
}

export function RunMapView({ snapshot, location }: ViewProps) {
  const identity = location.fixture || "summary-active";
  const incoming = snapshot.run;
  const [paused, setPaused] = useState(false);
  const [heldRun, setHeldRun] = useState<RunDetail | null>(() => incoming ? runForIdentity(incoming, identity) : null);
  const [level, setLevel] = useState<DisclosureLevel>(() => initialLevel(identity));
  const [expanded, setExpanded] = useState(identity === "full-expanded" || identity === "blocked-causal" || identity === "malformed-topology");
  const [filter, setFilter] = useState<RunMapFilter>("all");
  const [query, setQuery] = useState("");
  const [selectedTicket, setSelectedTicket] = useState("");
  const [selectedGroup, setSelectedGroup] = useState("");
  const [causal, setCausal] = useState<CausalFocus | null>(null);

  const projectedIncoming = useMemo(() => incoming ? runForIdentity(incoming, identity) : null, [identity, incoming]);
  useEffect(() => { if (!paused) setHeldRun(projectedIncoming); }, [paused, projectedIncoming]);
  const run = paused ? heldRun : projectedIncoming;
  const topology = useMemo(() => buildTopology(run?.tickets ?? []), [run]);
  const visibleTickets = useMemo(
    () => filterTickets(run?.tickets ?? [], filter, query, topology.criticalPath),
    [filter, query, run, topology.criticalPath]
  );
  const graph = useMemo(
    () => projectedGraph(visibleTickets, expanded, selectedTicket, selectedGroup, causal),
    [causal, expanded, selectedGroup, selectedTicket, visibleTickets]
  );
  const ticket = run?.tickets.find((candidate) => candidate.id === selectedTicket) ?? null;
  const group = readinessGroups(run?.tickets ?? []).find((candidate) => candidate.id === selectedGroup) ?? null;

  useEffect(() => {
    if (identity !== "blocked-causal" || !run || selectedTicket) return;
    const waiting = run.tickets.find((candidate) => candidate.readiness.dependencies.length > 0);
    if (!waiting) return;
    setSelectedTicket(waiting.id);
    setCausal(authoritativeCausalFocus(waiting.id, run.tickets));
  }, [identity, run, selectedTicket]);

  function openTicket(id: string) {
    if (!run) return;
    setSelectedGroup("");
    setSelectedTicket(id);
    setCausal(null);
    setLevel(3);
  }

  function openGroup(next: ReadinessGroup) {
    setSelectedTicket("");
    setSelectedGroup(next.id);
    setCausal(null);
    setLevel(3);
  }

  function whyWaiting() {
    if (!run || !selectedTicket) return;
    setCausal((current) => current ? null : authoritativeCausalFocus(selectedTicket, run.tickets));
  }

  if (!run) return (
    <div className="foundation-view run-map" data-view="run-map"><div className="run-map__empty"><GitBranch aria-hidden="true" /><h1>No workflow selected</h1><p>Choose a workflow from the fleet to inspect its canonical graph.</p></div></div>
  );

  return (
    <div className="foundation-view run-map" data-view="run-map" data-fixture={identity} data-paused={paused}>
      <section className="run-map__hero" aria-labelledby="run-map-title">
        <div>
          <p className="run-map__eyebrow"><GitBranch aria-hidden="true" />Workflows · read-only topology</p>
          <h1 id="run-map-title">{run.id}</h1>
          <p>Expand from a faithful readiness summary into every canonical dependency.</p>
        </div>
        <div className="run-map__live">
          <span className={paused ? "is-paused" : "is-live"}><CircleDot aria-hidden="true" />{paused ? "snapshot held" : "safe live feed"}</span>
          <button type="button" onClick={() => setPaused((current) => !current)} aria-pressed={paused}>
            {paused ? <Play aria-hidden="true" /> : <Pause aria-hidden="true" />}{paused ? "Resume live" : "Pause live"}
          </button>
        </div>
      </section>

      <nav className="run-map__crumbs" aria-label="Run map disclosure">
        <button type="button" aria-current={level === 0 ? "page" : undefined} onClick={() => setLevel(0)}>Fleet</button>
        <ChevronRight aria-hidden="true" />
        <button type="button" aria-current={level === 1 ? "page" : undefined} onClick={() => setLevel(1)}>{run.id}</button>
        {level >= 2 && <><ChevronRight aria-hidden="true" /><button type="button" aria-current={level === 2 ? "page" : undefined} onClick={() => setLevel(2)}>Canonical graph</button></>}
        {level === 3 && <><ChevronRight aria-hidden="true" /><span aria-current="page">Inspector</span></>}
      </nav>

      {level === 0 && <FleetView runs={snapshot.runs} currentRun={run.id} onOpen={() => setLevel(1)} />}
      {level === 1 && <SummaryView run={run} onGroup={openGroup} onExpand={() => setLevel(2)} />}
      {level >= 2 && <section className={`run-map__workspace ${level === 3 ? "has-inspector" : ""}`}>
        <article className="run-map__graph-card" aria-labelledby="canonical-graph-heading">
          <header className="run-map__graph-heading">
            <div><p className="run-map__eyebrow">Level 2 · topology</p><h2 id="canonical-graph-heading">{expanded ? "Every canonical dependency" : "Readiness groups collapsed"}</h2></div>
            <button type="button" className="run-map__expand" aria-pressed={expanded} onClick={() => setExpanded((current) => !current)}>
              {expanded ? <Box aria-hidden="true" /> : <Maximize2 aria-hidden="true" />}{expanded ? "Collapse groups" : "Expand all tickets"}
            </button>
          </header>
          <div className="run-map__toolbar" aria-label="Graph filters">
            <label className="run-map__search"><Search aria-hidden="true" /><span className="sr-only">Search by ticket id or executor</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search ticket or executor" /></label>
            <div className="run-map__filters" role="group" aria-label="Filter work items">
              {FILTERS.map((item) => <button key={item.id} type="button" aria-pressed={filter === item.id} onClick={() => setFilter(item.id)}>{item.label}</button>)}
            </div>
          </div>
          <div className="run-map__canvas" data-causal={causal ? "active" : "off"}>
            {visibleTickets.length > 0 ? <ReactFlowProvider>
              <ReactFlow
                aria-label="Canonical run dependency graph"
                nodes={graph.nodes}
                edges={graph.edges}
                nodeTypes={nodeTypes}
                nodesDraggable={false}
                nodesConnectable={false}
                edgesReconnectable={false}
                elementsSelectable
                nodesFocusable
                edgesFocusable
                deleteKeyCode={null}
                fitView
                minZoom={0.35}
                maxZoom={1.8}
                onNodeClick={(_, node) => node.type === "group" ? openGroup((node.data as GroupNodeData).group) : openTicket(node.id)}
                proOptions={{ hideAttribution: true }}
              >
                <Background gap={24} size={1} />
                <MiniMap ariaLabel="Run graph minimap" pannable zoomable />
                <Controls showInteractive={false} aria-label="Pan, zoom, and fit graph" />
              </ReactFlow>
            </ReactFlowProvider> : <div className="run-map__no-match"><Search aria-hidden="true" /><strong>No matching work items</strong><button type="button" onClick={() => { setFilter("all"); setQuery(""); }}>Clear filters</button></div>}
          </div>
          <footer className="run-map__legend" aria-label="Status legend">
            {(["waiting", "ready", "running", "attention", "complete", "unknown"] as const).map((state) => <span key={state} data-status={state}><i aria-hidden="true">{statusGlyph(state)}</i>{state}</span>)}
          </footer>
        </article>
        {level === 3 && <Inspector ticket={ticket} group={group} causal={causal} onWhy={whyWaiting} onClose={() => { setLevel(2); setCausal(null); }} />}
      </section>}

      {topology.diagnostics.length > 0 && <section className="run-map__diagnostics" aria-labelledby="diagnostics-heading">
        <header><AlertTriangle aria-hidden="true" /><div><p className="run-map__eyebrow">Topology diagnostics</p><h2 id="diagnostics-heading">{topology.diagnostics.length} canonical graph {topology.diagnostics.length === 1 ? "issue" : "issues"}</h2></div></header>
        <ul>{topology.diagnostics.map((diagnostic) => <li key={diagnostic.id}><strong>{diagnostic.kind}</strong><span>{diagnostic.message}</span></li>)}</ul>
      </section>}
      <p className="run-map__status sr-only" aria-live="polite">{paused ? "Live updates paused; the displayed snapshot is held." : "Live updates enabled."}</p>
      <div className="run-map__read-only"><LockKeyhole aria-hidden="true" /><span>Observe only</span>No graph, ticket, or workflow controls can mutate state.</div>
    </div>
  );
}
