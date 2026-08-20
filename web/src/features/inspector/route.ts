export interface InspectorRoute {
  run: string;
  ticket: string;
  fixture: string;
}

interface RouteLocation {
  pathname: string;
  search: string;
  hash: string;
}

function decode(value: string): string | null {
  try {
    return decodeURIComponent(value);
  } catch {
    return null;
  }
}

export const route = {
  match(location: RouteLocation): InspectorRoute | null {
    const match = /^\/runs\/([^/]+)\/tickets\/([^/]+)\/?$/.exec(location.pathname);
    if (!match) return null;
    const run = decode(match[1]);
    const ticket = decode(match[2]);
    if (run === null || ticket === null) return null;
    return { run, ticket, fixture: new URLSearchParams(location.search).get("fixture") ?? "" };
  },
  build(value: InspectorRoute): string {
    const query = new URLSearchParams();
    if (value.fixture) query.set("fixture", value.fixture);
    const search = query.toString();
    const path = `/runs/${encodeURIComponent(value.run)}/tickets/${encodeURIComponent(value.ticket)}`;
    return `${path}${search ? `?${search}` : ""}`;
  },
};
