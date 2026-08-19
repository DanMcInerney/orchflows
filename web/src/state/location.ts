import type { ViewId } from "../api/schema";

export interface LocationState {
  view: ViewId;
  run: string;
  ticket: string;
  session: string;
  fixture: string;
}

function decoded(value: string | undefined): string {
  if (!value) return "";
  try { return decodeURIComponent(value); } catch { return ""; }
}

export function parseLocation(location: Pick<Location, "pathname" | "search"> = window.location): LocationState {
  const parts = location.pathname.split("/").filter(Boolean);
  const fixture = new URLSearchParams(location.search).get("fixture") ?? "";
  if (parts[0] === "runs" && parts[1] && parts[2] === "tickets" && parts[3]) {
    return { view: "ticket", run: decoded(parts[1]), ticket: decoded(parts[3]), session: "", fixture };
  }
  if (parts[0] === "runs") {
    return { view: "run-map", run: decoded(parts[1]), ticket: "", session: "", fixture };
  }
  if (parts[0] === "sessions" && parts[1]) {
    return { view: "session-graph", run: "", ticket: "", session: decoded(parts[1]), fixture };
  }
  if (parts[0] === "sessions") return { view: "sessions", run: "", ticket: "", session: "", fixture };
  if (parts[0] === "friction") return { view: "friction", run: "", ticket: "", session: "", fixture };
  return { view: "now", run: "", ticket: "", session: "", fixture };
}

export function pathFor(view: ViewId, selection: Partial<LocationState> = {}): string {
  const run = encodeURIComponent(selection.run ?? "");
  const ticket = encodeURIComponent(selection.ticket ?? "");
  const session = encodeURIComponent(selection.session ?? "");
  if (view === "run-map") return run ? `/runs/${run}` : "/runs/";
  if (view === "ticket") return `/runs/${run}/tickets/${ticket}`;
  if (view === "sessions") return "/sessions";
  if (view === "session-graph") return `/sessions/${session}`;
  if (view === "friction") return "/friction";
  return "/now";
}
