import * as Tooltip from "@radix-ui/react-tooltip";
import { Eye, LockKeyhole, Radio, RefreshCw } from "lucide-react";
import { useEffect, useMemo } from "react";
import { matchCatalog } from "../catalog";
import { featureCatalog } from "./featureCatalog";
import { useBrowserLocation } from "./useBrowserLocation";

export function Shell() {
  const [location, navigate] = useBrowserLocation();
  const match = useMemo(
    () => matchCatalog(featureCatalog, location),
    [location.pathname, location.search, location.hash],
  );

  useEffect(() => {
    if (match !== null && !match.isCanonical) {
      window.history.replaceState({}, "", match.canonicalHref);
    }
  }, [match]);

  const navigation = featureCatalog.flatMap((entry) => {
    if (entry.kind === "disabled") return [entry];
    return entry.navigation === false ? [] : [entry];
  });
  const FeatureHost = match?.View;

  return (
    <Tooltip.Provider delayDuration={300}>
      <main data-mode="observe" className="shell">
        <header className="masthead">
          <a className="brand" href="/now" onClick={(event) => {
            event.preventDefault();
            navigate("/now");
          }}>
            <Eye aria-hidden="true" /><span>orchflows</span>
          </a>
          <div className="mode"><Radio aria-hidden="true" /> Observe</div>
          <Tooltip.Root>
            <Tooltip.Trigger asChild>
              <span className="read-only" tabIndex={0}>
                <LockKeyhole aria-hidden="true" /> read only
              </span>
            </Tooltip.Trigger>
            <Tooltip.Portal>
              <Tooltip.Content className="tooltip" sideOffset={8}>
                This view cannot start, edit, or delete a run.
              </Tooltip.Content>
            </Tooltip.Portal>
          </Tooltip.Root>
        </header>
        <div className="workspace">
          <nav className="rail" aria-label="Observe views">
            <p className="rail__label">Workspace</p>
            {navigation.map((entry) => {
              if (entry.kind === "disabled") {
                return (
                  <span
                    key={entry.id}
                    className="rail__disabled"
                    aria-disabled="true"
                    title={entry.navigation.reason}
                  >
                    <span aria-hidden="true" className="nav-dot" />
                    {entry.navigation.label}
                    <small>future</small>
                    <span className="sr-only">{entry.navigation.reason}</span>
                  </span>
                );
              }
              const current = match?.activeNavigationId === entry.activeNavigationId;
              const href = entry.navigationHref as string;
              const label = entry.navigation === false ? entry.id : entry.navigation.label;
              return (
                <a
                  key={entry.id}
                  href={href}
                  aria-current={current ? "page" : undefined}
                  onClick={(event) => {
                    event.preventDefault();
                    navigate(href);
                  }}
                >
                  <span aria-hidden="true" className="nav-dot" />{label}
                </a>
              );
            })}
            <div className="rail__status">
              <RefreshCw aria-hidden="true" /><span>Safe live feed</span>
            </div>
          </nav>
          <section className="content" aria-live="polite">
            {FeatureHost
              ? <FeatureHost />
              : (
                <section className="foundation-view" aria-labelledby="not-found-title">
                  <h1 id="not-found-title">View not found</h1>
                  <p>The requested reader view is not registered.</p>
                </section>
              )}
          </section>
        </div>
      </main>
    </Tooltip.Provider>
  );
}
