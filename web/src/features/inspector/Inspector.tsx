import * as Tabs from "@radix-ui/react-tabs";
import {
  AlertTriangle, ArrowRight, CheckCircle2, CircleDot, CircleHelp, Clock3,
  Code2, FileCheck2, Flame, History, LayoutDashboard, ListChecks, LockKeyhole
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import type { ExperienceSnapshot } from "../../api/schema";
import type { LocationState } from "../../state/location";
import {
  detailRows, durableHistory, inspectorTabs, linkedFriction, proofRows, rawTicket,
  selectedTab, statusState, tabPath, type InspectorTab
} from "./model";
import "./inspector.css";

export const viewId = "ticket" as const;

export interface TicketInspectorProps {
  snapshot: ExperienceSnapshot;
  location: LocationState;
}

const tabLabels: Record<InspectorTab, string> = {
  overview: "Overview", details: "Details", proof: "Proof",
  friction: "Friction", history: "History", raw: "Raw"
};

const tabIcons: Record<InspectorTab, ReactNode> = {
  overview: <LayoutDashboard aria-hidden="true" />,
  details: <ListChecks aria-hidden="true" />,
  proof: <FileCheck2 aria-hidden="true" />,
  friction: <Flame aria-hidden="true" />,
  history: <History aria-hidden="true" />,
  raw: <Code2 aria-hidden="true" />
};

function EmptyEvidence({ title, children }: { title: string; children: ReactNode }) {
  return <div className="inspector-empty"><CircleHelp aria-hidden="true" /><h3>{title}</h3><p>{children}</p></div>;
}

export default function TicketInspector({ snapshot, location }: TicketInspectorProps) {
  const [tab, setTab] = useState<InspectorTab>(() => selectedTab(location));
  const ticket = snapshot.ticket;

  useEffect(() => {
    const sync = () => setTab(selectedTab(location));
    window.addEventListener("popstate", sync);
    sync();
    return () => window.removeEventListener("popstate", sync);
  }, [location.fixture, location.run, location.ticket]);

  if (!ticket) {
    return <section className="foundation-view ticket-inspector" aria-labelledby="ticket-title"><EmptyEvidence title="Ticket unavailable">The selected ticket is not present in the safe reader projection.</EmptyEvidence></section>;
  }

  const state = statusState(ticket);
  const rows = proofRows(snapshot, location.fixture);
  const friction = linkedFriction(snapshot, location);
  const history = durableHistory(snapshot, location);
  const objective = ticket.sections.objective || "No objective was recorded.";
  const result = ticket.sections.result;

  const changeTab = (value: string) => {
    const next = value as InspectorTab;
    setTab(next);
    window.history.pushState({}, "", tabPath(next));
  };

  return (
    <section className="foundation-view ticket-inspector" data-state={state} data-fixture={location.fixture || "live"} aria-labelledby="ticket-title">
      <header className="inspector-header">
        <div className="inspector-breadcrumb" aria-label="Ticket location">
          <span>Workflows</span><ArrowRight aria-hidden="true" /><span className="mono">{location.run}</span><ArrowRight aria-hidden="true" />
          <strong className="mono">{ticket.id}</strong>
        </div>
        <div className="inspector-heading">
          <div>
            <p className="eyebrow">Inspector evidence</p>
            <h1 id="ticket-title">{ticket.id}</h1>
            <p>{objective}</p>
          </div>
          <div className="inspector-status" data-state={state} aria-label={`Ticket state: ${state}`}>
            <CircleDot aria-hidden="true" /><span>{state}</span><small>{ticket.status}</small>
          </div>
        </div>
      </header>

      <Tabs.Root className="inspector-tabs" value={tab} onValueChange={changeTab} orientation="horizontal">
        <Tabs.List className="inspector-tablist" aria-label="Ticket inspector sections">
          {inspectorTabs.map((item) => (
            <Tabs.Trigger key={item} className="inspector-tab" value={item}>
              {tabIcons[item]}<span>{tabLabels[item]}</span>
              {item === "proof" && <small aria-label={`${rows.length} criteria`}>{rows.length}</small>}
              {item === "friction" && friction.length > 0 && <small aria-label={`${friction.length} linked records`}>{friction.length}</small>}
            </Tabs.Trigger>
          ))}
        </Tabs.List>

        <Tabs.Content className="inspector-panel" value="overview">
          <div className="overview-grid">
            <article className="inspector-card inspector-card--objective">
              <p className="eyebrow">What this is</p><h2>Active objective</h2><p>{objective}</p>
              {result && <div className="result-note"><CheckCircle2 aria-hidden="true" /><div><strong>Recorded result</strong><p>{result}</p></div></div>}
            </article>
            <article className="inspector-card inspector-card--phase">
              <p className="eyebrow">What is happening</p><h2>Current phase</h2>
              <div className="phase-state" data-state={state}><CircleDot aria-hidden="true" /><strong>{state}</strong><span>{ticket.status}</span></div>
              <p>{ticket.readiness.explanation || "No readiness explanation was projected."}</p>
            </article>
            <article className="inspector-card inspector-card--next">
              <p className="eyebrow">What happens next</p><h2>Next transition</h2>
              <div className="next-step"><ArrowRight aria-hidden="true" /><p>{ticket.readiness.dependencies.length ? `Waiting on ${ticket.readiness.dependencies.join(", ")}.` : state === "complete" ? "Review the recorded proof and result." : "The assigned worker continues within the ticket limit."}</p></div>
            </article>
          </div>
        </Tabs.Content>

        <Tabs.Content className="inspector-panel" value="details">
          <article className="inspector-card"><div className="panel-heading"><p className="eyebrow">Canonical metadata</p><h2>Routing and limits</h2></div>
            <dl className="detail-list">{detailRows(ticket).map((row) => <div key={row.label}><dt>{row.label}</dt><dd className={row.mono ? "mono" : undefined}>{row.value}</dd></div>)}</dl>
          </article>
        </Tabs.Content>

        <Tabs.Content className="inspector-panel" value="proof">
          <article className="inspector-card"><div className="panel-heading"><p className="eyebrow">Verification evidence</p><h2>Criteria and verdicts</h2><p>Every projected criterion keeps its oracle class and evidence identity.</p></div>
            {rows.length ? <div className="proof-list" role="list" aria-label="Verification criteria">{rows.map((row) => {
              const verdict = row.verdict.toLowerCase();
              const Icon = verdict === "pass" ? CheckCircle2 : verdict === "fail" ? AlertTriangle : CircleHelp;
              return <article className="proof-row" data-verdict={verdict} role="listitem" key={`${row.criterion}-${row.oracle}`}>
                <div className="proof-verdict"><Icon aria-hidden="true" /><span>{row.verdict}</span><small>Criterion {row.criterion}</small></div>
                <div><span className="field-label">Oracle</span><strong className="mono">{row.oracle}</strong></div>
                <div><span className="field-label">Class</span><span>{row.oracleClass}</span></div>
                <div><span className="field-label">Evidence</span><code>{row.evidence}</code></div>
              </article>;
            })}</div> : <EmptyEvidence title="Proof unavailable">No verification rows were projected. Unknown is preserved; it is not treated as a pass.</EmptyEvidence>}
          </article>
        </Tabs.Content>

        <Tabs.Content className="inspector-panel" value="friction">
          <article className="inspector-card"><div className="panel-heading"><p className="eyebrow">Linked by run and ticket</p><h2>Friction records</h2></div>
            {friction.length ? <div className="friction-list">{friction.map((item, index) => <article className="friction-record" key={`${item.ts}-${index}`}>
              <header><AlertTriangle aria-hidden="true" /><strong>{item.category}</strong><time>{item.ts}</time></header>
              <dl><div><dt>Observed</dt><dd>{item.observed}</dd></div><div><dt>Expected</dt><dd>{item.expected}</dd></div><div><dt>Host</dt><dd>{item.host}</dd></div></dl>
            </article>)}</div> : <EmptyEvidence title="No linked friction">No friction record names both this run and this ticket.</EmptyEvidence>}
          </article>
        </Tabs.Content>

        <Tabs.Content className="inspector-panel" value="history">
          <article className="inspector-card"><div className="panel-heading"><p className="eyebrow">Durable evidence only</p><h2>History</h2></div>
            {history.length ? <ol className="history-list">{history.map((item, index) => <li key={`${item.ts}-${index}`}><Clock3 aria-hidden="true" /><div><strong>{item.event}</strong><p>{item.detail || "No durable detail recorded."}</p><span>{item.agent} · {item.ts}</span></div></li>)}</ol> : <EmptyEvidence title="History unavailable">No durable claim or event evidence is available for this ticket. Activity is not inferred from transcripts.</EmptyEvidence>}
          </article>
        </Tabs.Content>

        <Tabs.Content className="inspector-panel" value="raw">
          <article className="inspector-card"><div className="panel-heading"><p className="eyebrow">Inert source</p><h2>Raw ticket markdown</h2><p className="raw-privacy"><LockKeyhole aria-hidden="true" /> Host paths are redacted. Markup is displayed as text and never executed.</p></div>
            <pre className="raw-ticket" tabIndex={0} aria-label="Raw ticket markdown"><code>{rawTicket(snapshot, location)}</code></pre>
          </article>
        </Tabs.Content>
      </Tabs.Root>
    </section>
  );
}
