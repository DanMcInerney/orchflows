export interface SessionGraphRoute {
  session: string;
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
  match(location: RouteLocation): SessionGraphRoute | null {
    const match = /^\/sessions\/([^/]+)\/?$/.exec(location.pathname);
    if (!match) return null;
    const session = decode(match[1]);
    if (session === null) return null;
    return { session, fixture: new URLSearchParams(location.search).get("fixture") ?? "" };
  },
  build(value: SessionGraphRoute): string {
    const query = new URLSearchParams();
    if (value.fixture) query.set("fixture", value.fixture);
    const search = query.toString();
    const path = `/sessions/${encodeURIComponent(value.session)}`;
    return `${path}${search ? `?${search}` : ""}`;
  },
};
