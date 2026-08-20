import {
  AlertTriangle,
  ArrowRight,
  Clock3,
  FileQuestion,
  FileWarning,
  Link2,
  LockKeyhole,
  Server,
} from "lucide-react";
import { useEffect, useState } from "react";
import type { FeatureState } from "../../shared/transport/types";
import { linkedCaptureRecord } from "./fixtures";
import { closedFrictionRecord, type FrictionModel, type FrictionRecord } from "./model";
import type { FrictionRoute } from "./route";
import "./friction.css";

export interface FrictionViewProps {
  route: FrictionRoute;
  state: FeatureState<FrictionModel>;
}

const FRICTION_PAGE_SIZE = 50;

function timestamp(value = ""): string {
  const matched = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})(?::\d{2})?Z$/.exec(value);
  return matched ? `${matched[1]} ${matched[2]} UTC` : value || "Time unavailable";
}

function countLabel(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}

function linkedPath(run: string, ticket = ""): string {
  const runPath = `/runs/${encodeURIComponent(run)}`;
  return ticket ? `${runPath}/tickets/${encodeURIComponent(ticket)}` : runPath;
}

function RecordLinkage({ record }: { record: FrictionRecord }) {
  if (!record.run && !record.ticket) {
    return <span className="friction-record__unlinked">No run or ticket recorded</span>;
  }
  return (
    <span className="friction-record__links" aria-label="Linked workflow evidence">
      <Link2 aria-hidden="true" />
      {record.run ? <a href={linkedPath(record.run)}><span>Run</span> <code>{record.run}</code></a> : <span>Run unavailable</span>}
      {record.ticket && record.run ? (
        <>
          <ArrowRight aria-hidden="true" />
          <a href={linkedPath(record.run, record.ticket)}><span>Ticket</span> <code>{record.ticket}</code></a>
        </>
      ) : record.ticket ? <span>Ticket <code>{record.ticket}</code> (run unavailable)</span> : null}
    </span>
  );
}

function FrictionRecordCard({ record, index }: { record: FrictionRecord; index: number }) {
  const headingId = `friction-record-${index}`;
  return (
    <article className="friction-record" aria-labelledby={headingId}>
      <header className="friction-record__header">
        <div>
          <h2 id={headingId}>{record.observed || "Observed condition unavailable"}</h2>
        </div>
        <time dateTime={record.ts || undefined}><Clock3 aria-hidden="true" />{timestamp(record.ts)}</time>
      </header>
      <div className="friction-record__expectation">
        <span>Expected</span>
        <p>{record.expected || "No expected condition was recorded."}</p>
      </div>
      <footer className="friction-record__footer">
        <RecordLinkage record={record} />
        <span className="friction-record__host"><Server aria-hidden="true" />{record.host || "Host unavailable"}</span>
      </footer>
    </article>
  );
}

function IntegrityNotice({ skipped, unreadable }: { skipped: number; unreadable: number }) {
  const total = skipped + unreadable;
  if (!total) return null;
  return (
    <section className="friction-integrity" aria-labelledby="friction-integrity-title">
      <AlertTriangle aria-hidden="true" />
      <div>
        <h2 id="friction-integrity-title">Some log records need attention</h2>
        <p>
          {countLabel(unreadable, "unreadable record")} and {countLabel(skipped, "skipped line")} were omitted.
          Valid records below remain available.
        </p>
      </div>
    </section>
  );
}

export function FrictionView({ route, state }: FrictionViewProps) {
  const [visibleLimit, setVisibleLimit] = useState(FRICTION_PAGE_SIZE);
  useEffect(() => setVisibleLimit(FRICTION_PAGE_SIZE), [route.fixture]);
  const fixtureEmpty = route.fixture === "empty";
  const projectedItems = fixtureEmpty
    ? []
    : state.model?.items.map(closedFrictionRecord).filter((item): item is FrictionRecord => item !== null) ?? [];
  const items = route.fixture === "populated" && !projectedItems.some((item) => item.run && item.ticket)
    ? [linkedCaptureRecord, ...projectedItems]
    : projectedItems;
  const skipped = fixtureEmpty ? 0 : Math.max(0, state.model?.skipped ?? 0);
  const unreadable = fixtureEmpty ? 0 : Math.max(0, state.model?.unreadable ?? 0);
  const visibleItems = items.slice(0, visibleLimit);

  if (!route.fixture && state.status === "loading") return <div className="loading">Waiting for reader</div>;
  if (!route.fixture && state.status === "error") return <div className="notice" role="status">{state.error.message}</div>;

  return (
    <div className="friction-view foundation-view" data-view="friction" data-state={items.length ? "populated" : "empty"}>
      {state.status === "stale" && <div className="notice" role="status">{state.error.message}</div>}
      <IntegrityNotice skipped={skipped} unreadable={unreadable} />
      <header className="friction-hero">
        <div>
          <p className="friction-eyebrow"><FileWarning aria-hidden="true" />Problem log</p>
          <h1>Friction</h1>
          <p>Read-only diagnostics show what happened, what was expected, and the exact workflow evidence available.</p>
        </div>
        <div className="friction-count" aria-label={countLabel(items.length, "friction record")}>
          <strong>{items.length}</strong>
          <span>{items.length === 1 ? "record" : "records"}</span>
        </div>
      </header>

      {items.length ? (
        <>
          <section className="friction-feed" aria-label="Friction records">
            {visibleItems.map((record, index) => <FrictionRecordCard key={`${record.ts || "undated"}-${index}`} record={record} index={index} />)}
          </section>
          <div className="friction-feed__more" role="status">
            <span>Showing {visibleItems.length} of {items.length} records</span>
            {visibleItems.length < items.length && <button
              type="button"
              onClick={() => setVisibleLimit((limit) => Math.min(limit + FRICTION_PAGE_SIZE, items.length))}
              aria-label={`Show ${Math.min(FRICTION_PAGE_SIZE, items.length - visibleItems.length)} more friction records`}
            >Show {Math.min(FRICTION_PAGE_SIZE, items.length - visibleItems.length)} more</button>}
          </div>
        </>
      ) : (
        <section className="friction-empty" aria-labelledby="friction-empty-title">
          <span className="friction-empty__glyph"><FileQuestion aria-hidden="true" /></span>
          <div>
            <h2 id="friction-empty-title">No friction records available</h2>
            <p>This state sink has no readable problem-log entries. New records will appear here without changing workflow state.</p>
          </div>
        </section>
      )}

      <aside className="friction-privacy" aria-label="Privacy boundary">
        <LockKeyhole aria-hidden="true" />
        <p><strong>Safe projection.</strong> Prompts, tools, command output, file contents, host paths, and conversations are never shown.</p>
      </aside>
    </div>
  );
}

export default FrictionView;
