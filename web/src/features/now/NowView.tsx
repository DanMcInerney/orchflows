import { AlertTriangle, ArrowRight, Check, Circle, Clock3, Filter, GitBranch, Pause, Play, Radio, ShieldAlert } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { executionRunRoute, executionTicketRoute } from "../../shared/routes/executionRoutes";
import type { FeatureState } from "../../shared/transport/types";
import { nowFixture } from "./fixtures";
import { bandLabel, projectFleet, projectWork, type FleetRun, type NowModel, type NowTicket } from "./model";
import type { NowRoute } from "./route";
import "./now.css";

export interface NowViewProps {
  route: NowRoute;
  state: FeatureState<NowModel>;
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

function ExecutionFlow({ run }: { run: FleetRun }) {
  return <figure className="now-flow" aria-label={`Compact execution summary for ${run.id}`}>
    <div className="now-flow__visual" aria-hidden="true">
      {run.groups.length ? run.groups.map((group, index) => <span className="now-flow__step" data-state={group.state} key={group.id}>
        {index > 0 && <ArrowRight />}
        {stateGlyph(group.state)}
        <b>{group.label}</b>
        <small>{group.ticketIds.length}</small>
      </span>) : <span className="now-flow__empty">No canonical ticket steps</span>}
    </div>
    <ol className="sr-only" aria-label={`Nonvisual execution summary for ${run.id}`}>
      {run.groups.map((group, index) => <li key={group.id}>
        Step {index + 1}: {group.label}; {group.state}; {group.ticketIds.length} {group.ticketIds.length === 1 ? "ticket" : "tickets"}
      </li>)}
    </ol>
  </figure>;
}

function TicketList({ label, tickets, run, fixture, emptyText }: {
  label: string; tickets: NowTicket[]; run: string; fixture: string; emptyText: string;
}) {
  return <section className="now-work" aria-label={`${label} for ${run}`}>
    <h4>{label}</h4>
    {tickets.length ? <ul>{tickets.map((ticket) => <li key={ticket.id} data-state={ticket.readiness.state}>
      {stateGlyph(ticket.readiness.state)}
      <a href={executionTicketRoute.build({ run, ticket: ticket.id, fixture })} aria-label={`Open ticket: ${ticket.title ?? ticket.id}`}>
        <strong>{ticket.title ?? ticket.id}</strong><code>{ticket.id}</code>
      </a>
      <span>{ticket.status}</span>
    </li>)}</ul> : <p>{emptyText}</p>}
  </section>;
}

function RunCard({ run, fixture, historical = false }: { run: FleetRun; fixture: string; historical?: boolean }) {
  const work = projectWork(run.tickets);
  return <article className="now-run-card" data-band={run.band}>
    <header>
      <span className="now-run-card__state">{stateGlyph(run.band === "completed" ? "complete" : run.band === "attention" ? "attention" : "running")}{bandLabel[run.band]}</span>
      <CountSummary counts={run.counts} />
    </header>
    <div className="now-run-card__identity">
      <div>
        <h3 className="now-objective-summary" title={run.objective}>
          <a href={executionRunRoute.build({ run: run.id, fixture })} aria-label={`Open run: ${run.objective}`}>{run.objective}</a>
        </h3>
        <p><GitBranch aria-hidden="true" /> {run.repository}</p>
      </div>
      <span><Clock3 aria-hidden="true" /> {run.lastActivity}</span>
    </div>
    <details className="now-objective-details"><summary>Full objective</summary><p>{run.objective}</p></details>
    {run.unreadable || work.unknown.length ? <div className="now-unknown" role="status">
      <ShieldAlert aria-hidden="true" /><span><strong>Unknown progress</strong>Canonical ticket data is unavailable; no progress was inferred.</span>
    </div> : <>
      <ExecutionFlow run={run} />
      {historical ? <p className="now-history-note"><Check aria-hidden="true" /> Completed with {run.tickets.length} exact {run.tickets.length === 1 ? "ticket" : "tickets"}. Open the run for full evidence.</p>
        : <div className="now-work-grid">
          <TicketList label="Current" tickets={work.current} run={run.id} fixture={fixture} emptyText="No ticket is currently executing." />
          <TicketList label="Next" tickets={work.next} run={run.id} fixture={fixture} emptyText="No ticket is ready next." />
        </div>}
    </>}
    <a className="now-run-card__open" href={executionRunRoute.build({ run: run.id, fixture })}>Open full execution <ArrowRight aria-hidden="true" /></a>
  </article>;
}

function EmptyCurrent({ filtered }: { filtered: boolean }) {
  return <div className="now-empty" role="status">
    {filtered ? <Filter aria-hidden="true" /> : <Check aria-hidden="true" />}
    <strong>{filtered ? "No runs match this filter." : "No current work"}</strong>
    <span>{filtered ? "Choose All runs to restore the full execution hierarchy." : "There is nothing active or waiting for attention."}</span>
  </div>;
}

export default function NowView({ route, state }: NowViewProps) {
  const fixture = useMemo(() => route.fixture ? nowFixture(route.fixture) : null, [route.fixture]);
  const incoming = useMemo(() => fixture?.runs ?? state.model?.runs ?? [], [fixture, state.model]);
  const initialPaused = fixture?.paused ?? false;
  const [paused, setPaused] = useState(initialPaused);
  const [frozen, setFrozen] = useState(incoming);
  const [filter, setFilter] = useState<"all" | "attention">("all");

  useEffect(() => { if (!paused) setFrozen(incoming); }, [incoming, paused]);
  useEffect(() => { setPaused(initialPaused); }, [initialPaused, route.fixture]);
  const fleet = useMemo(() => projectFleet(frozen), [frozen]);
  const visible = filter === "attention" ? fleet.filter((run) => run.band === "attention") : fleet;
  const current = visible.filter((run) => run.band !== "completed");
  const history = visible.filter((run) => run.band === "completed");

  if (!fixture && state.status === "loading") return <div className="loading">Waiting for reader</div>;
  if (!fixture && state.status === "error") return <div className="notice" role="status">{state.error.message}</div>;

  return <div className="foundation-view now-view" data-fixture={route.fixture || "live"}>
    {state.status === "stale" && <div className="notice" role="status">{state.error.message}</div>}
    <header className="now-header">
      <div><p className="now-kicker"><Radio aria-hidden="true" /> Execution overview</p><h1>Now</h1><p>Current execution first, exact next work beside it, and recent history below.</p></div>
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
    <main className="now-hierarchy">
      <section className="now-section" aria-labelledby="now-current-heading">
        <header><div><p className="now-kicker">Live execution</p><h2 id="now-current-heading">Current work</h2></div><b>{current.length}</b></header>
        {current.length ? <div className="now-run-list">{current.map((run) => <RunCard key={run.id} run={run} fixture={route.fixture} />)}</div>
          : <EmptyCurrent filtered={filter === "attention"} />}
      </section>
      {filter === "all" && <section className="now-section now-section--history" aria-labelledby="now-history-heading">
        <header><div><p className="now-kicker">Completed</p><h2 id="now-history-heading">Recent history</h2></div><b>{history.length}</b></header>
        {history.length ? <div className="now-run-list">{history.map((run) => <RunCard key={run.id} run={run} fixture={route.fixture} historical />)}</div>
          : <div className="now-empty"><Clock3 aria-hidden="true" /><strong>No recent runs</strong><span>Completed work will appear here.</span></div>}
      </section>}
    </main>
    <p className="now-privacy">Only canonical status and metadata are shown. Prompts, tools, outputs, files, and conversations remain private.</p>
  </div>;
}
