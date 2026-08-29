import * as Tabs from "@radix-ui/react-tabs";
import {
  Activity, AlertTriangle, ArrowRight, CheckCircle2, CircleHelp, Clock3,
  Code2, ExternalLink, FileCheck2, Flame, History, LayoutDashboard, ListChecks,
  LockKeyhole, PackageOpen, XCircle
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import type { FeatureState } from "../../shared/transport/types";
import {
  artifactRows, detailRows, durableHistory, executorSource, fixtureTicket, inspectorTabs,
  linkedFriction, proofRows, rawTicket, selectedTab, statusState, tabPath,
  type InspectorModel, type InspectorTab
} from "./model";
import type { InspectorRoute } from "./route";
import "./inspector.css";

export interface TicketInspectorProps {
  route: InspectorRoute;
  state: FeatureState<InspectorModel>;
}

const tabLabels: Record<InspectorTab, string> = {
  overview: "Overview", details: "Details", proof: "Proof",
  artifacts: "Artifacts", friction: "Friction", history: "History", raw: "Raw"
};

const tabIcons: Record<InspectorTab, ReactNode> = {
  overview: <LayoutDashboard aria-hidden="true" />,
  details: <ListChecks aria-hidden="true" />,
  proof: <FileCheck2 aria-hidden="true" />,
  artifacts: <PackageOpen aria-hidden="true" />,
  friction: <Flame aria-hidden="true" />,
  history: <History aria-hidden="true" />,
  raw: <Code2 aria-hidden="true" />
};

function EmptyEvidence({ title, children }: { title: string; children: ReactNode }) {
  return <div className="inspector-empty"><CircleHelp aria-hidden="true" /><h3>{title}</h3><p>{children}</p></div>;
}

function StateGlyph({ state }: { state: string }) {
  if (state === "running") return <Activity aria-hidden="true" />;
  if (state === "complete") return <CheckCircle2 aria-hidden="true" />;
  if (state === "failed") return <XCircle aria-hidden="true" />;
  if (state === "attention") return <AlertTriangle aria-hidden="true" />;
  if (state === "waiting") return <Clock3 aria-hidden="true" />;
  if (state === "ready") return <ArrowRight aria-hidden="true" />;
  return <CircleHelp aria-hidden="true" />;
}

export default function TicketInspector({ route, state: featureState }: TicketInspectorProps) {
  const [tab, setTab] = useState<InspectorTab>(() => selectedTab(route));
  const namedFixture = fixtureTicket(route);
  const ticket = route.fixture.startsWith("proof-")
    ? namedFixture
    : featureState.model?.ticket ?? namedFixture;
  const viewModel: InspectorModel = ticket === featureState.model?.ticket
    ? featureState.model ?? { run: null, ticket: null }
    : { run: featureState.model?.run ?? null, ticket };

  useEffect(() => {
    const sync = () => setTab(selectedTab(route));
    window.addEventListener("popstate", sync);
    sync();
    return () => window.removeEventListener("popstate", sync);
  }, [route.fixture, route.run, route.ticket]);

  if (!route.fixture && featureState.status === "loading") return <div className="loading">Waiting for reader</div>;
  if (!route.fixture && featureState.status === "error") return <div className="notice" role="status">{featureState.error.message}</div>;

  if (!ticket) {
    return <section className="foundation-view ticket-inspector" aria-labelledby="ticket-title"><EmptyEvidence title="Ticket unavailable">The selected ticket is not present in the safe reader projection.</EmptyEvidence></section>;
  }

  const state = statusState(ticket);
  const rows = proofRows(viewModel, route.fixture);
  const source = executorSource(ticket);
  const artifacts = artifactRows(ticket, route);
  const friction = linkedFriction(viewModel, route);
  const history = durableHistory(viewModel, route);
  const objective = ticket.sections.objective || "No objective was recorded.";
  const result = ticket.sections.result;
  const claim = ticket.claimed_by && ticket.claimed_at ? `${ticket.claimed_by} · ${ticket.claimed_at}` : "Unclaimed";
  const agents = Array.from(new Set(history.map((item) => item.agent).filter(Boolean)));
  const stats: Array<{ label: string; value: number }> = [
    { label: "Criteria", value: rows.length },
    { label: "Depends", value: ticket.depends_on.length },
    { label: "Friction", value: friction.length },
    { label: "Events", value: history.length }
  ];
  const identities = [
    ticket.executor || "executor unavailable",
    ticket.pack || "pack unavailable",
    ticket.bound ? `bound ${ticket.bound}` : "bound unavailable"
  ];

  const changeTab = (value: string) => {
    const next = value as InspectorTab;
    setTab(next);
    window.history.pushState({}, "", tabPath(next));
  };

  return (
    <section className="foundation-view ticket-inspector" data-state={state} data-fixture={route.fixture || "live"} aria-labelledby="ticket-title">
      {featureState.status === "stale" && <div className="notice" role="status">{featureState.error.message}</div>}
      <div className="inspector-breadcrumb" aria-label="Ticket location">
        <span>Now</span><ArrowRight aria-hidden="true" /><span className="mono">{route.run}</span><ArrowRight aria-hidden="true" />
        <strong className="mono">{ticket.id}</strong>
      </div>
      <header className="inspector-hero">
        <div className="inspector-hero__identity">
          <p className="eyebrow">Inspector evidence</p>
          <div className="inspector-hero__title">
            <h1 id="ticket-title">{ticket.id}</h1>
            <div className="inspector-status" data-state={state} aria-label={`Ticket state: ${state}`}>
              <StateGlyph state={state} /><span>{state}</span><small>{ticket.status}</small>
            </div>
          </div>
          <p className="inspector-lede">{ticket.readiness.explanation || "No readiness explanation was projected."}</p>
          <div className="inspector-identities" aria-label="Ticket routing identities">
            {identities.map((item) => <span key={item}>{item}</span>)}
          </div>
        </div>
        <dl className="inspector-stats">
          {stats.map((item) => <div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>)}
        </dl>
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
              <div className="phase-state" data-state={state}><StateGlyph state={state} /><strong>{state}</strong><span>{ticket.status}</span></div>
              <dl className="fact-rows">
                <div><dt>Cause</dt><dd className="mono">{ticket.readiness.cause}</dd></div>
                <div><dt>Claim</dt><dd>{claim}</dd></div>
                {ticket.readiness.causal_chain.length > 0 && <div><dt>Chain</dt><dd className="mono">{ticket.readiness.causal_chain.join(" → ")}</dd></div>}
              </dl>
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
            <div className="source-disclosure">
              <div><p className="eyebrow">Canonical association</p><h3>Executor source</h3></div>
              {source.href
                ? <a href={source.href} aria-label={`Open canonical ${source.label}`}><ExternalLink aria-hidden="true" /><span>{source.label}</span></a>
                : <div className="unavailable-state"><strong>Executor source unavailable</strong><p>{source.reason}</p></div>}
            </div>
          </article>
        </Tabs.Content>

        <Tabs.Content className="inspector-panel" value="proof">
          <article className="inspector-card"><div className="panel-heading"><p className="eyebrow">Verification evidence</p><h2>Criteria and verdicts</h2><p>Every projected criterion keeps its oracle class and evidence identity.</p></div>
            <section className="judgment-summary" aria-labelledby="judgment-title">
              <div className="judgment-heading"><p className="eyebrow">Canonical fields only</p><h3 id="judgment-title">Judgment explanation</h3></div>
              <dl className="fact-rows">
                {["result", "feedback", "risks"].map((name) => <div key={name}><dt>{name}</dt><dd>{ticket.sections[name] || "Unavailable"}</dd></div>)}
                <div><dt>Rationale</dt><dd>{ticket.judgment?.rationale.state === "available" && ticket.judgment.rationale.identity
                  ? <code>{ticket.judgment.rationale.identity.id}</code>
                  : <><strong>Rationale unavailable</strong><span>No canonical rationale identity was recorded.</span></>}</dd></div>
              </dl>
            </section>
            {rows.some((row) => row.verdict.toLowerCase() === "fail") && <div className="proof-alert" role="status"><AlertTriangle aria-hidden="true" /><div><strong>Criterion {rows.find((row) => row.verdict.toLowerCase() === "fail")?.criterion} failed</strong><p>{rows.find((row) => row.verdict.toLowerCase() === "fail")?.oracle}: {rows.find((row) => row.verdict.toLowerCase() === "fail")?.evidence}</p></div></div>}
            {rows.length ? <div className="proof-list" role="list" aria-label="Verification criteria">{rows.map((row) => {
              const verdict = row.verdict.toLowerCase();
              const Icon = verdict === "pass" ? CheckCircle2 : verdict === "fail" ? AlertTriangle : CircleHelp;
              return <article className="proof-row" data-verdict={verdict} role="listitem" key={`${row.criterion}-${row.oracle}`}>
                <div className="proof-verdict"><Icon aria-hidden="true" /><span>{row.verdict}</span><small>Criterion {row.criterion}</small></div>
                <div className="proof-oracle"><span className="field-label">Oracle</span><strong className="mono">{row.oracle}</strong></div>
                <details className="disclosure proof-evidence" open={verdict !== "pass"}>
                  <summary>Criterion {row.criterion} evidence</summary>
                  <dl>
                    <div><dt>Class</dt><dd><span>{row.oracleClass}</span></dd></div>
                    <div><dt>Identity</dt><dd><code>{row.evidence}</code></dd></div>
                  </dl>
                </details>
              </article>;
            })}</div> : <EmptyEvidence title="Proof unavailable">No verification rows were projected. Unknown is preserved; it is not treated as a pass.</EmptyEvidence>}
          </article>
        </Tabs.Content>

        <Tabs.Content className="inspector-panel" value="artifacts">
          <article className="inspector-card"><div className="panel-heading"><p className="eyebrow">State-sink identities only</p><h2>Generated artifacts</h2><p>Links use opaque projected identities and the contained artifact reader.</p></div>
            {ticket.artifacts?.state === "rows" && artifacts.length
              ? <div className="artifact-list" role="list" aria-label="Generated artifacts">{artifacts.map((item, index) => <article className="artifact-row" role="listitem" key={`${item.id}-${index}`}>
                <div><strong>{item.label}</strong><span>{item.mediaType}</span></div>
                {item.href
                  ? <a href={item.href} aria-label={`Open contained artifact ${item.label}`}><ExternalLink aria-hidden="true" /><span>Open contained artifact</span></a>
                  : <div className="unavailable-state"><span className="field-label">Unavailable</span><strong>{item.reason}</strong>{item.reason !== item.label && <p>{item.label}</p>}</div>}
              </article>)}</div>
              : <EmptyEvidence title="Artifacts unavailable">{ticket.artifacts?.reason || "No canonical artifact identities were projected."}</EmptyEvidence>}
          </article>
        </Tabs.Content>

        <Tabs.Content className="inspector-panel" value="friction">
          <article className="inspector-card"><div className="panel-heading"><p className="eyebrow">Linked by run and ticket</p><h2>Friction records</h2></div>
            {friction.length ? <div className="friction-list" role="list" aria-label="Linked friction records">{friction.map((item, index) => <article className="friction-row" role="listitem" key={`${item.ts}-${index}`}>
              <div className="friction-row__headline"><AlertTriangle aria-hidden="true" /><strong>{item.observed}</strong><time className="mono">{item.ts}</time></div>
              <details className="disclosure friction-row__detail">
                <summary>Expectation and host</summary>
                <dl><div><dt>Expected</dt><dd>{item.expected}</dd></div><div><dt>Host</dt><dd className="mono">{item.host}</dd></div></dl>
              </details>
            </article>)}</div> : <EmptyEvidence title="No linked friction">No friction record names both this run and this ticket.</EmptyEvidence>}
          </article>
        </Tabs.Content>

        <Tabs.Content className="inspector-panel" value="history">
          <article className="inspector-card"><div className="panel-heading"><p className="eyebrow">Durable evidence only</p><h2>History</h2>
            {agents.length > 0 && <p>{agents.length === 1 ? "One agent identity" : `${agents.length} agent identities`} recorded across {history.length} durable {history.length === 1 ? "event" : "events"}.</p>}</div>
            {history.length ? <ol className="history-list" aria-label="Durable ticket events">{history.map((item, index) => <li className="history-row" key={`${item.ts}-${index}`}>
              <span className="history-row__glyph"><Clock3 aria-hidden="true" /></span>
              <strong>{item.event}</strong>
              <time className="mono">{item.ts}</time>
              <span className="history-row__agent mono">{item.agent}</span>
              {item.detail
                ? <details className="disclosure history-row__detail"><summary>Durable detail</summary><p>{item.detail}</p></details>
                : <p className="history-row__detail history-row__detail--empty">No durable detail recorded.</p>}
            </li>)}</ol> : <EmptyEvidence title="History unavailable">No durable claim or event evidence is available for this ticket. Activity is not inferred from transcripts.</EmptyEvidence>}
          </article>
        </Tabs.Content>

        <Tabs.Content className="inspector-panel" value="raw">
          <article className="inspector-card"><div className="panel-heading"><p className="eyebrow">Inert source</p><h2>Raw ticket markdown</h2><p className="raw-privacy"><LockKeyhole aria-hidden="true" /> Host paths are redacted. Markup is displayed as text and never executed.</p></div>
            <pre className="raw-ticket" tabIndex={0} aria-label="Raw ticket markdown"><code>{rawTicket(viewModel, route)}</code></pre>
          </article>
        </Tabs.Content>
      </Tabs.Root>
    </section>
  );
}
