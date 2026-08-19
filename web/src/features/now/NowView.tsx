import { AlertTriangle, Check, ChevronDown, ChevronRight, Circle, Clock3, Filter, GitBranch, Pause, Play, Radio, ShieldAlert } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { ViewProps } from "../../app/registry";
import type { TicketSummary } from "../../api/schema";
import { RunGraph } from "../../graph/RunGraph";
import { nowFixture } from "./fixtures";
import { bandLabel, projectFleet, type FleetRun, type NowBand, type NowRun } from "./model";
import "./now.css";

export const viewId = "now" as const;

function liveRuns({ runs }: ViewProps["snapshot"]): NowRun[] {
  return runs.map((summary) => {
    return {
      id: summary.id,
      objective: summary.objective || summary.id,
      repository: summary.repository || "Repository unavailable",
      client: summary.client || undefined,
      lastActivity: summary.last_activity || "Activity unavailable",
      tickets: summary.tickets,
      unreadable: summary.unreadable || (!summary.tickets.length && summary.ticket_count > 0),
    };
  });
}

function stateGlyph(state: string) {
  if (state === "attention") return <AlertTriangle aria-hidden="true" />;
  if (state === "complete") return <Check aria-hidden="true" />;
  if (state === "running") return <Radio aria-hidden="true" />;
  if (state === "unknown") return <ShieldAlert aria-hidden="true" />;
  return <Circle aria-hidden="true" />;
}

function CountSummary({ counts }: { counts: Record<string, number> }) {
  const entries = Object.entries(counts).filter(([, count]) => count > 0);
  return <span className="now-counts" aria-label={entries.map(([name, count]) => `${count} ${name}`).join(", ")}>
    {entries.map(([name, count]) => <span key={name}><b>{count}</b> {name}</span>)}
  </span>;
}

function RunRow({ run, selected, onSelect }: { run: FleetRun; selected: boolean; onSelect: () => void }) {
  return <button type="button" className="now-run" data-band={run.band} aria-pressed={selected} onClick={onSelect}>
    <span className="now-run__tone" aria-hidden="true">{stateGlyph(run.band === "attention" ? "attention" : run.band === "completed" ? "complete" : "running")}</span>
    <span className="now-run__copy">
      <strong>{run.objective}</strong>
      <span><GitBranch aria-hidden="true" /> {run.repository}</span>
      <span className="now-run__path">{run.path || "Canonical groups unavailable"}</span>
    </span>
    <span className="now-run__meta"><CountSummary counts={run.counts} /><small><Clock3 aria-hidden="true" /> {run.lastActivity}</small></span>
  </button>;
}

function FleetBand({ band, runs, selected, onSelect }: {
  band: NowBand; runs: FleetRun[]; selected: string; onSelect: (id: string) => void;
}) {
  const [open, setOpen] = useState(band !== "completed");
  if (!runs.length && band === "completed") return null;
  return <section className="now-band" aria-labelledby={`now-band-${band}`}>
    <button type="button" className="now-band__heading" onClick={() => setOpen((value) => !value)} aria-expanded={open} aria-label={`${bandLabel[band]}, ${runs.length} runs`}>
      {open ? <ChevronDown aria-hidden="true" /> : <ChevronRight aria-hidden="true" />}
      <span id={`now-band-${band}`}>{bandLabel[band]}</span><b>{runs.length}</b>
    </button>
    {open && <div className="now-band__rows">
      {runs.length ? runs.map((run) => <RunRow key={run.id} run={run} selected={selected === run.id} onSelect={() => onSelect(run.id)} />)
        : <p className="now-band__empty">{band === "active" ? "No active runs. Waiting and completed work remains available." : "No runs need attention."}</p>}
    </div>}
  </section>;
}

function GroupStrip({ run, expanded, onToggle }: { run: FleetRun; expanded: Set<string>; onToggle: (id: string) => void }) {
  return <ol className="now-groups" aria-label={`${run.objective} computed path`}>
    {run.groups.map((group) => <li key={group.id}>
      <button type="button" data-state={group.state} aria-expanded={expanded.has(group.id)} onClick={() => onToggle(group.id)}>
        {stateGlyph(group.state)}<span>{group.label}</span><b>{group.ticketIds.length}</b>
      </button>
      {expanded.has(group.id) && <div className="now-group-detail">
        <p>Exact child tickets</p>
        <ul>{group.ticketIds.map((id) => <li key={id}><code>{id}</code></li>)}</ul>
        <p>{group.edges.length ? group.edges.map((edge) => `${edge.source} → ${edge.target}`).join(" · ") : "No internal dependency edges"}</p>
      </div>}
    </li>)}
  </ol>;
}

function Inspector({ run, tab, setTab }: { run: FleetRun; tab: string; setTab: (tab: string) => void }) {
  const tabs = ["summary", "tickets"];
  return <aside className="now-inspector" aria-labelledby="now-inspector-heading">
    <p className="now-kicker">Inspector evidence</p><h2 id="now-inspector-heading">{run.objective}</h2>
    <div className="now-tabs" role="tablist" aria-label="Run inspector">
      {tabs.map((name, index) => <button
        type="button"
        role="tab"
        key={name}
        aria-selected={tab === name}
        tabIndex={tab === name ? 0 : -1}
        onClick={() => setTab(name)}
        onKeyDown={(event) => {
          if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
          event.preventDefault();
          const offset = event.key === "ArrowRight" ? 1 : -1;
          const next = (index + offset + tabs.length) % tabs.length;
          setTab(tabs[next]);
          event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next]?.focus();
        }}
      >{name}</button>)}
    </div>
    <div role="tabpanel" tabIndex={0}>
      {tab === "summary" ? <dl>
        <div><dt>Run</dt><dd><code>{run.id}</code></dd></div>
        <div><dt>Band</dt><dd>{bandLabel[run.band]}</dd></div>
        <div><dt>Workspace</dt><dd>{run.repository}</dd></div>
        {run.client && <div><dt>Client</dt><dd>{run.client}</dd></div>}
        <div><dt>Activity</dt><dd>{run.lastActivity}</dd></div>
      </dl> : <ul className="now-ticket-list">{run.tickets.map((ticket) => <li key={ticket.id} data-state={ticket.readiness.state}>
        {stateGlyph(ticket.readiness.state)}<span><code>{ticket.id}</code><small>{ticket.title ?? ticket.readiness.explanation}</small></span><b>{ticket.status}</b>
      </li>)}</ul>}
    </div>
    <p className="now-privacy">Only canonical status and metadata are shown. Prompts, tools, outputs, files, and conversations remain private.</p>
  </aside>;
}

export default function NowView({ snapshot, location }: ViewProps) {
  const fixture = useMemo(() => location.fixture ? nowFixture(location.fixture) : null, [location.fixture]);
  const incoming = useMemo(() => fixture?.runs ?? liveRuns(snapshot), [fixture, snapshot]);
  const initialPaused = fixture?.paused ?? false;
  const [paused, setPaused] = useState(initialPaused);
  const [frozen, setFrozen] = useState(incoming);
  const [selectedId, setSelectedId] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [tab, setTab] = useState("summary");
  const [filter, setFilter] = useState<"all" | "attention">("all");

  useEffect(() => { if (!paused) setFrozen(incoming); }, [incoming, paused]);
  useEffect(() => { setPaused(initialPaused); }, [initialPaused, location.fixture]);
  const fleet = useMemo(() => projectFleet(frozen), [frozen]);
  const visible = filter === "attention" ? fleet.filter((run) => run.band === "attention") : fleet;
  const selected = fleet.find((run) => run.id === selectedId) ?? visible[0] ?? fleet[0];
  useEffect(() => { if (selected && selected.id !== selectedId) setSelectedId(selected.id); }, [selected, selectedId]);
  const toggleGroup = (id: string) => setExpanded((current) => {
    const next = new Set(current); next.has(id) ? next.delete(id) : next.add(id); return next;
  });

  return <div className="foundation-view now-view" data-fixture={location.fixture || "live"}>
    <header className="now-header">
      <div><p className="now-kicker"><Radio aria-hidden="true" /> Fleet overview</p><h1>Now</h1><p>Every eligible run, ordered by what needs you first.</p></div>
      <div className="now-live" role="status" aria-live="polite" data-paused={paused}>
        <span>{paused ? <Pause aria-hidden="true" /> : <Radio aria-hidden="true" />}{paused ? "Live paused" : "Live · checking for changes"}</span>
        <button type="button" aria-pressed={paused} onClick={() => setPaused((value) => !value)}>{paused ? <Play aria-hidden="true" /> : <Pause aria-hidden="true" />}{paused ? "Resume live" : "Pause live"}</button>
      </div>
    </header>
    {fixture?.diagnostic && <div className="now-diagnostic" role="status"><ShieldAlert aria-hidden="true" /><span><strong>Unreadable canonical data</strong>{fixture.diagnostic}</span></div>}
    <div className="now-toolbar" aria-label="Fleet filters">
      <Filter aria-hidden="true" /><span>Filter</span>
      <button type="button" aria-pressed={filter === "all"} onClick={() => setFilter("all")}>All runs</button>
      <button type="button" aria-pressed={filter === "attention"} onClick={() => setFilter("attention")}>Needs attention</button>
      <small>{visible.length} visible</small>
    </div>
    <div className="now-layout">
      <div className="now-fleet" aria-label="Run fleet">
        {(["attention", "active", "completed"] as NowBand[]).map((band) => <FleetBand key={band} band={band} runs={visible.filter((run) => run.band === band)} selected={selected?.id ?? ""} onSelect={setSelectedId} />)}
      </div>
      <main className="now-map" aria-labelledby="now-map-heading">
        {selected ? <>
          <header><div><p className="now-kicker">Active objective</p><h2 id="now-map-heading">{selected.objective}</h2></div><CountSummary counts={selected.counts} /></header>
          <GroupStrip run={selected} expanded={expanded} onToggle={toggleGroup} />
          <div className="now-graph" aria-label="Expanded canonical dependency graph">
            {selected.tickets.length && !selected.unreadable ? <RunGraph tickets={selected.tickets as TicketSummary[]} /> : <div className="now-unavailable"><ShieldAlert aria-hidden="true" /><strong>Exact graph unavailable</strong><span>The run stays visible until its canonical tickets can be read.</span></div>}
          </div>
        </> : <div className="now-unavailable"><Check aria-hidden="true" /><strong>No eligible runs</strong><span>There is nothing active or recently completed in the safe projection.</span></div>}
      </main>
      {selected && <Inspector run={selected} tab={tab} setTab={setTab} />}
    </div>
  </div>;
}
