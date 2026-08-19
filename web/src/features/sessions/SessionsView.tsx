import { AlertTriangle, Clock3, FolderSearch, LockKeyhole, Search, UsersRound } from "lucide-react";
import { useMemo, useState } from "react";

import type { ExperienceSnapshot } from "../../api/schema";
import type { LocationState } from "../../state/location";
import { fixtureSessions, sessionLabel, sessionsModel } from "./model";
import "./sessions.css";

export interface SessionsViewProps {
  snapshot: ExperienceSnapshot;
  location: LocationState;
}

function diagnosticCount(model: ReturnType<typeof sessionsModel>): number {
  return new Set([
    ...model.diagnostics,
    ...model.items.flatMap((item) => item.diagnostics)
  ]).size;
}

export function SessionsView({ snapshot, location }: SessionsViewProps) {
  const [query, setQuery] = useState("");
  const model = useMemo(
    () => fixtureSessions(sessionsModel(snapshot.sessions), location.fixture),
    [location.fixture, snapshot.sessions]
  );
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const visible = normalizedQuery
    ? model.items.filter((item) => `${item.title} ${item.id}`.toLocaleLowerCase().includes(normalizedQuery))
    : model.items;
  const diagnostics = diagnosticCount(model);

  return (
    <div className="sessions-view" data-view="sessions" data-fixture={location.fixture || "live"}>
      <section className="sessions-view__hero hero" aria-labelledby="sessions-title">
        <div>
          <p className="eyebrow"><LockKeyhole aria-hidden="true" /> Safe metadata index</p>
          <h1 id="sessions-title">Sessions</h1>
          <p>Discoverable session identities and agent counts, without conversation content.</p>
        </div>
        <div className="hero__metric" aria-label={`${model.items.length} discoverable sessions`}>
          <strong>{model.items.length}</strong><span>sessions</span>
        </div>
      </section>

      {model.diagnostics.length > 0 && (
        <div className="sessions-view__diagnostic" role="status">
          <AlertTriangle aria-hidden="true" />
          <div><strong>Metadata needs attention</strong><span>{model.diagnostics.join(" ")}</span></div>
        </div>
      )}

      <section className="sessions-view__index" aria-labelledby="session-index-heading">
        <header className="sessions-view__toolbar">
          <div>
            <p className="eyebrow">Canonical discovery</p>
            <h2 id="session-index-heading">Session index</h2>
            <p>{diagnostics ? `${diagnostics} diagnostic ${diagnostics === 1 ? "signal" : "signals"}` : "All reported metadata is readable"}</p>
          </div>
          {!model.empty && (
            <label className="sessions-view__search">
              <span className="sr-only">Filter sessions by title or identity</span>
              <Search aria-hidden="true" />
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Filter title or identity"
              />
            </label>
          )}
        </header>

        {model.empty ? (
          <div className="sessions-view__empty" role="status">
            <FolderSearch aria-hidden="true" />
            <div><h3>No sessions discovered</h3><p>The configured transcript root contains no canonically addressable sessions.</p></div>
          </div>
        ) : visible.length === 0 ? (
          <div className="sessions-view__empty" role="status">
            <Search aria-hidden="true" />
            <div><h3>No matching sessions</h3><p>Clear the filter to return to the complete safe metadata index.</p></div>
          </div>
        ) : (
          <ul className="sessions-view__list" aria-label="Discoverable sessions">
            {visible.map((item) => (
              <li key={item.id} data-diagnostic={item.diagnostics.length > 0 || undefined}>
                <a href={`/sessions/${encodeURIComponent(item.id)}`} aria-label={`Open ${sessionLabel(item)}`}>
                  <span className="sessions-view__identity">
                    <strong>{sessionLabel(item)}</strong>
                    <span className="mono">{item.id}</span>
                  </span>
                  <span className="sessions-view__unknown">
                    <FolderSearch aria-hidden="true" />
                    <span>{item.client || "Unknown client"}<small>{item.project || "Project metadata unavailable"}</small></span>
                  </span>
                  <span className="sessions-view__agents"><UsersRound aria-hidden="true" /> {item.agentCount} {item.agentCount === 1 ? "agent" : "agents"}</span>
                  <span className="sessions-view__modified"><Clock3 aria-hidden="true" /> {item.modified || "Activity not reported"}</span>
                  <span className="sessions-view__diagnostic-count">
                    {item.diagnostics.length ? <><AlertTriangle aria-hidden="true" /> {item.diagnostics.length} diagnostic</> : "Metadata ready"}
                  </span>
                </a>
              </li>
            ))}
          </ul>
        )}
      </section>

      <p className="sessions-view__privacy privacy-note">
        <LockKeyhole aria-hidden="true" /> Prompts, tool activity, command output, file contents, paths, and conversations are excluded.
      </p>
    </div>
  );
}
