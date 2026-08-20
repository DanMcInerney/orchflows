export interface RunMapRoute {
  run: string;
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
  match(location: RouteLocation): RunMapRoute | null {
    const match = /^\/runs(?:\/([^/]+))?\/?$/.exec(location.pathname);
    if (!match) return null;
    const run = match[1] ? decode(match[1]) : "";
    if (run === null) return null;
    return { run, fixture: new URLSearchParams(location.search).get("fixture") ?? "" };
  },
  build(value: RunMapRoute): string {
    const base = value.run ? `/runs/${encodeURIComponent(value.run)}` : "/runs/";
    const query = new URLSearchParams();
    if (value.fixture) query.set("fixture", value.fixture);
    const search = query.toString();
    return `${base}${search ? `?${search}` : ""}`;
  },
};
