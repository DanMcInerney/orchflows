export const EXECUTION_ROUTE_PARENT = "now" as const;

export interface ExecutionRunRoute {
  run: string;
  fixture: string;
}

export interface ExecutionTicketRoute extends ExecutionRunRoute {
  ticket: string;
}

export interface RouteLocation {
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

function fixture(search: string): string {
  return new URLSearchParams(search).get("fixture") ?? "";
}

function withFixture(path: string, value: string): string {
  const query = new URLSearchParams();
  if (value) query.set("fixture", value);
  const search = query.toString();
  return `${path}${search ? `?${search}` : ""}`;
}

export const executionRunRoute = {
  match(location: RouteLocation): ExecutionRunRoute | null {
    const match = /^\/runs(?:\/([^/]+))?\/?$/.exec(location.pathname);
    if (!match) return null;
    const run = match[1] ? decode(match[1]) : "";
    if (run === null) return null;
    return { run, fixture: fixture(location.search) };
  },
  build(value: ExecutionRunRoute): string {
    const path = value.run ? `/runs/${encodeURIComponent(value.run)}` : "/runs/";
    return withFixture(path, value.fixture);
  },
};

export const executionTicketRoute = {
  match(location: RouteLocation): ExecutionTicketRoute | null {
    const match = /^\/runs\/([^/]+)\/tickets\/([^/]+)\/?$/.exec(location.pathname);
    if (!match) return null;
    const run = decode(match[1]);
    const ticket = decode(match[2]);
    if (run === null || ticket === null) return null;
    return { run, ticket, fixture: fixture(location.search) };
  },
  build(value: ExecutionTicketRoute): string {
    const path = `/runs/${encodeURIComponent(value.run)}/tickets/${encodeURIComponent(value.ticket)}`;
    return withFixture(path, value.fixture);
  },
};
