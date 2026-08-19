import * as Tooltip from "@radix-ui/react-tooltip";
import { Activity, AlertTriangle, Eye, LockKeyhole, Radio, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { registeredViews } from "./app/registry";
import type { ExperienceSnapshot, NavigationItem, ViewId } from "./api/schema";
import { useExperienceFeed } from "./feed";
import { RunGraph } from "./graph/RunGraph";
import { fixtureText, fixtureTickets } from "./testing/fixtures";
import { parseLocation, pathFor, type LocationState } from "./state/location";

function isViewId(id: NavigationItem["id"]): id is ViewId { return id !== "create"; }

const FALLBACK_NAVIGATION: NavigationItem[] = [
  { id: "now", label: "Now", path: "/now", disabled: false, explanation: "" },
  { id: "run-map", label: "Workflows", path: "/runs/", disabled: false, explanation: "" },
  {
    id: "create", label: "Create", path: "", disabled: true,
    explanation: "Future workflow authoring is unavailable in this read-only observer."
  },
  { id: "sessions", label: "Sessions", path: "/sessions", disabled: false, explanation: "" },
  { id: "friction", label: "Friction", path: "/friction", disabled: false, explanation: "" }
];

function useLocationState(): [LocationState, (view: ViewId) => void] {
  const [location, setLocation] = useState(() => parseLocation());
  useEffect(() => {
    const changed = () => setLocation(parseLocation());
    window.addEventListener("popstate", changed);
    return () => window.removeEventListener("popstate", changed);
  }, []);
  const navigate = (view: ViewId) => {
    const path = pathFor(view, location);
    window.history.pushState({}, "", path);
    setLocation(parseLocation());
  };
  return [location, navigate];
}

function FoundationView({ snapshot, location }: { snapshot: ExperienceSnapshot; location: LocationState }) {
  const copy = fixtureText(location.fixture);
  const tickets = location.fixture ? fixtureTickets(location.fixture) : snapshot.run?.tickets ?? [];
  return (
    <div className="foundation-view" data-view={location.view} data-fixture={location.fixture || "live"}>
      <section className="hero" aria-labelledby="view-title">
        <div>
          <p className="eyebrow"><Activity aria-hidden="true" /> {copy.eyebrow}</p>
          <h1 id="view-title">{copy.title}</h1>
          <p>{copy.note}</p>
        </div>
        <div className="hero__metric" aria-label={`${tickets.length} work items`}>
          <strong>{tickets.length}</strong><span>work items</span>
        </div>
      </section>
      <section className="view-grid">
        <article className="graph-card" aria-labelledby="graph-heading">
          <header className="card-heading">
            <div><p className="eyebrow">Current topology</p><h2 id="graph-heading">Dependency map</h2></div>
            <span className="live-chip"><Radio aria-hidden="true" /> {tickets.some((item) => item.readiness.state === "running") ? "live" : "settled"}</span>
          </header>
          <div className="graph-frame">
            {tickets.length ? <RunGraph tickets={tickets} /> : <p className="empty-state">No work items in this state.</p>}
          </div>
        </article>
        <aside className="evidence-card" aria-labelledby="evidence-heading">
          <p className="eyebrow">Inspector evidence</p>
          <h2 id="evidence-heading">Safe projection</h2>
          <dl>
            <div><dt>Schema</dt><dd>experience.v1</dd></div>
            <div><dt>Run</dt><dd className="mono">{location.run || snapshot.selection.run || "none"}</dd></div>
            <div><dt>State</dt><dd>{location.fixture || "live"}</dd></div>
          </dl>
          <p className="privacy-note"><LockKeyhole aria-hidden="true" /> Prompts, tools, command output, files, and conversations remain private.</p>
        </aside>
      </section>
    </div>
  );
}

export function ObserveApp() {
  const [location, navigate] = useLocationState();
  const { snapshot, unavailable } = useExperienceFeed(location);
  const views = useMemo(registeredViews, []);
  const FeatureView = views[location.view];
  const navigation = snapshot?.navigation ?? FALLBACK_NAVIGATION;

  return (
    <Tooltip.Provider delayDuration={300}>
      <main data-mode="observe" className="shell">
        <header className="masthead">
          <a className="brand" href="/now" onClick={(event) => { event.preventDefault(); navigate("now"); }}>
            <Eye aria-hidden="true" /><span>orchflows</span>
          </a>
          <div className="mode"><Radio aria-hidden="true" /> Observe</div>
          <Tooltip.Root>
            <Tooltip.Trigger asChild>
              <span className="read-only" tabIndex={0}><LockKeyhole aria-hidden="true" /> read only</span>
            </Tooltip.Trigger>
            <Tooltip.Portal><Tooltip.Content className="tooltip" sideOffset={8}>This view cannot start, edit, or delete a run.</Tooltip.Content></Tooltip.Portal>
          </Tooltip.Root>
        </header>
        <div className="workspace" aria-busy={!snapshot}>
          <nav className="rail" aria-label="Observe views">
            <p className="rail__label">Workspace</p>
            {navigation.map((item) => {
              if (item.disabled || !isViewId(item.id)) return (
                <span key={item.id} className="rail__disabled" aria-disabled="true" title={item.explanation}>
                  <span aria-hidden="true" className="nav-dot" />{item.label}<small>future</small>
                  <span className="sr-only">{item.explanation}</span>
                </span>
              );
              const viewId = item.id;
              const current = location.view === viewId
                || (viewId === "run-map" && location.view === "ticket")
                || (viewId === "sessions" && location.view === "session-graph");
              return (
                <a key={viewId} href={pathFor(viewId, location)} aria-current={current ? "page" : undefined}
                  onClick={(event) => { event.preventDefault(); navigate(viewId); }}>
                  <span aria-hidden="true" className="nav-dot" />{item.label}
                </a>
              );
            })}
            <div className="rail__status"><RefreshCw aria-hidden="true" /><span>{unavailable ? "Reader unavailable; retrying" : "Safe live feed"}</span></div>
          </nav>
          <section className="content" aria-live="polite">
            {unavailable && <div className="notice" role="status"><AlertTriangle aria-hidden="true" /> Reader unavailable; the last safe snapshot remains visible.</div>}
            {snapshot ? (
              FeatureView ? <FeatureView snapshot={snapshot} location={location} /> : <FoundationView snapshot={snapshot} location={location} />
            ) : <div className="loading"><span className="pulse" aria-hidden="true" />Waiting for reader</div>}
          </section>
        </div>
      </main>
    </Tooltip.Provider>
  );
}
