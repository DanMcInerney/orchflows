export interface NowRoute {
  fixture: string;
}

interface RouteLocation {
  pathname: string;
  search: string;
  hash: string;
}

export const route = {
  match(location: RouteLocation): NowRoute | null {
    if (location.pathname !== "/" && location.pathname !== "/now" && location.pathname !== "/now/") return null;
    return { fixture: new URLSearchParams(location.search).get("fixture") ?? "" };
  },
  build(value: NowRoute): string {
    const query = new URLSearchParams();
    if (value.fixture) query.set("fixture", value.fixture);
    const search = query.toString();
    return `/now${search ? `?${search}` : ""}`;
  },
};
