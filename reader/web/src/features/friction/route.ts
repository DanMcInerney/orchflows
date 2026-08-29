export interface FrictionRoute {
  fixture: string;
}

interface RouteLocation {
  pathname: string;
  search: string;
  hash: string;
}

export const route = {
  match(location: RouteLocation): FrictionRoute | null {
    if (location.pathname !== "/friction" && location.pathname !== "/friction/") return null;
    return { fixture: new URLSearchParams(location.search).get("fixture") ?? "" };
  },
  build(value: FrictionRoute): string {
    const query = new URLSearchParams();
    if (value.fixture) query.set("fixture", value.fixture);
    const search = query.toString();
    return `/friction${search ? `?${search}` : ""}`;
  },
};
