import { AlertTriangle, ArrowRight, Check, Circle, Clock3, Filter, FolderGit2, Pause, Play, Radio, ShieldAlert } from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { executionRunRoute, executionTicketRoute } from "../../shared/routes/executionRoutes";
import type { FeatureState } from "../../shared/transport/types";
import { SummaryFlow } from "../workflows/view/SummaryFlow";
import { nowFixture } from "./fixtures";
import {
  bandLabel, projectFleet, projectFolders, projectWork, runSummary,
  type FleetRun, type NowFolder, type NowModel, type NowTicket,
} from "./model";
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

function plural(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}

function finished(run: FleetRun): boolean {
  return Boolean(run.terminalAt) || run.band === "completed";
}

function TaskLine({ run, fixture }: { run: FleetRun; fixture: string }) {
  if (finished(run)) {
    return <p className="now-run-card__task">
      {stateGlyph("complete")}
      <span>{run.terminalStatus || "Terminal state unrecorded"} · {plural(run.tickets.length, "ticket")} · {run.terminalAt || "finish time unrecorded"}</span>
    </p>;
  }
  const current: NowTicket[] = projectWork(run.tickets).current;
  if (!current.length) {
    return <p className="now-run-card__task">{stateGlyph("waiting")}<span>No ticket is currently executing.</span></p>;
  }
  return <p className="now-run-card__task">
    {stateGlyph("running")}
    <span>Working on {current.map((ticket, index) => <span key={ticket.id}>
      {index > 0 && ", "}
      <a href={executionTicketRoute.build({ run: run.id, ticket: ticket.id, fixture })}
        aria-label={`Open ticket: ${ticket.title ?? ticket.id}`}>{ticket.title ?? ticket.id}</a>
    </span>)}</span>
  </p>;
}

function RunCard({ run, fixture }: { run: FleetRun; fixture: string }) {
  const href = executionRunRoute.build({ run: run.id, fixture });
  const unknown = run.unreadable || projectWork(run.tickets).unknown.length > 0;
  const flow = runSummary(run);
  return <li className="now-run-card" data-band={run.band}>
    <div className="now-run-card__identity">
      <p className="now-run-card__meta">
        <span className="now-run-card__state">{stateGlyph(run.band === "completed" ? "complete" : run.band === "attention" ? "attention" : "running")}{bandLabel[run.band]}</span>
        <span><Clock3 aria-hidden="true" /> {run.lastActivity}</span>
      </p>
      <h4 className="now-objective-summary" title={run.objective}>
        <a href={href} aria-label={`Open run: ${run.objective}`}>{run.objective}</a>
      </h4>
      <TaskLine run={run} fixture={fixture} />
      <details className="now-objective-details"><summary>Full objective</summary><p>{run.objective}</p></details>
      <a className="now-run-card__open" href={href}
        aria-label={`${finished(run) ? "Open full run" : "Open live workflow"} for ${run.objective}`}>
        {finished(run) ? "Open full run" : "Open live workflow"} <ArrowRight aria-hidden="true" />
      </a>
    </div>
    {unknown ? <div className="now-unknown" role="status">
      <ShieldAlert aria-hidden="true" /><span><strong>Unknown progress</strong>Canonical ticket data is unavailable; no progress was inferred.</span>
    </div> : <SummaryFlow workflowId={run.id} summary={flow.summary} nodeStates={flow.nodeStates} />}
  </li>;
}

function FolderPanel({ folder, fixture, id, note }: { folder: NowFolder; fixture: string; id: string; note: string }) {
  return <section className="now-folder" aria-labelledby={id}>
    <header>
      <div>
        <p className="eyebrow"><FolderGit2 aria-hidden="true" /> Folder</p>
        <h3 id={id}>{folder.label}</h3>
      </div>
      <p>{note}</p>
    </header>
    <ul className="now-folder__list" aria-label={`Sessions in ${folder.label}`}>
      {folder.runs.map((run) => <RunCard key={run.id} run={run} fixture={fixture} />)}
    </ul>
  </section>;
}

function FolderBand({ id, eyebrow, heading, folders, fixture, note, empty }: {
  id: string; eyebrow: string; heading: string; folders: NowFolder[];
  fixture: string; note: (folder: NowFolder) => string; empty: ReactNode;
}) {
  const runs = folders.reduce((total, folder) => total + folder.runs.length, 0);
  return <section className="now-band" aria-labelledby={`${id}-heading`}>
    <header>
      <div><p className="eyebrow">{eyebrow}</p><h2 id={`${id}-heading`}>{heading}</h2></div>
      <p>{plural(runs, "session")} · {plural(folders.length, "folder")}</p>
    </header>
    {folders.length ? folders.map((folder, index) => <FolderPanel
      key={folder.key} folder={folder} fixture={fixture} id={`${id}-folder-${index}`} note={note(folder)} />) : empty}
  </section>;
}

function EmptyCurrent({ filtered }: { filtered: boolean }) {
  return <div className="now-empty" role="status">
    {filtered ? <Filter aria-hidden="true" /> : <Check aria-hidden="true" />}
    <strong>{filtered ? "No runs match this filter." : "No session is running"}</strong>
    <span>{filtered ? "Choose All runs to restore every folder." : "Nothing is active or waiting for attention right now."}</span>
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
  const { running, past } = useMemo(() => projectFolders(visible), [visible]);
  const runningRuns = running.reduce((total, folder) => total + folder.runs.length, 0);
  const folders = new Set([...running, ...past].map((folder) => folder.label)).size;

  if (!fixture && state.status === "loading") return <div className="loading">Waiting for reader</div>;
  if (!fixture && state.status === "error") return <div className="notice" role="status">{state.error.message}</div>;

  return <div className="foundation-view now-view" data-fixture={route.fixture || "live"}>
    {state.status === "stale" && <div className="notice" role="status">{state.error.message}</div>}
    <header className="now-hero">
      <div>
        <p className="eyebrow"><Radio aria-hidden="true" /> Execution overview</p>
        <h1>Now</h1>
        <p>Sessions running right now, grouped by the folder they run in. Finished sessions sit below, most recent folder first.</p>
      </div>
      <dl aria-label="Now summary">
        <div><dt>Running</dt><dd>{runningRuns}</dd></div>
        <div><dt>Folders</dt><dd>{folders}</dd></div>
        <div><dt>Finished</dt><dd>{past.reduce((total, folder) => total + folder.runs.length, 0)}</dd></div>
      </dl>
    </header>
    {fixture?.diagnostic && <div className="now-diagnostic" role="status"><ShieldAlert aria-hidden="true" /><span><strong>Unreadable canonical data</strong>{fixture.diagnostic}</span></div>}
    <div className="now-toolbar" aria-label="Fleet filters">
      <Filter aria-hidden="true" /><span>Filter</span>
      <button type="button" aria-pressed={filter === "all"} onClick={() => setFilter("all")}>All runs</button>
      <button type="button" aria-pressed={filter === "attention"} onClick={() => setFilter("attention")}>Needs attention</button>
      <div className="now-live" role="status" aria-live="polite" data-paused={paused}>
        <span>{paused ? <Pause aria-hidden="true" /> : <Radio aria-hidden="true" />}{paused ? "Live paused" : "Live · checking for changes"}</span>
        <button type="button" aria-pressed={paused} onClick={() => setPaused((value) => !value)}>{paused ? <Play aria-hidden="true" /> : <Pause aria-hidden="true" />}{paused ? "Resume live" : "Pause live"}</button>
      </div>
    </div>
    <main className="now-hierarchy">
      <FolderBand id="now-running" eyebrow="Live execution" heading="Running now" folders={running}
        fixture={route.fixture} note={(folder) => plural(folder.runs.length, "session")}
        empty={<EmptyCurrent filtered={filter === "attention"} />} />
      {filter === "all" && <FolderBand id="now-past" eyebrow="Finished" heading="Past sessions" folders={past}
        fixture={route.fixture} note={(folder) => `Newest finish ${folder.newestTerminal || "unrecorded"}`}
        empty={<div className="now-empty"><Clock3 aria-hidden="true" /><strong>No past sessions</strong><span>Finished work will appear here, grouped by folder.</span></div>} />}
    </main>
    <p className="now-privacy">Only canonical status and metadata are shown. Prompts, tools, outputs, files, and conversations remain private.</p>
  </div>;
}
