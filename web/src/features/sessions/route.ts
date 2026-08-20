export interface SessionsRoute {
  fixture: string;
}

interface RouteLocation {
  pathname: string;
  search: string;
  hash: string;
}

export const route = {
  match(location: RouteLocation): SessionsRoute | null {
    if (location.pathname !== "/sessions" && location.pathname !== "/sessions/") return null;
    return { fixture: new URLSearchParams(location.search).get("fixture") ?? "" };
  },
  build(value: SessionsRoute): string {
    const query = new URLSearchParams();
    if (value.fixture) query.set("fixture", value.fixture);
    const search = query.toString();
    return `/sessions${search ? `?${search}` : ""}`;
  },
};
