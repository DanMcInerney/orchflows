interface RouteLocation {
  pathname: string;
  search: string;
  hash: string;
}

export interface WorkflowListRoute {
  fixture: string;
}

export interface WorkflowDetailRoute {
  workflowId: string;
  fixture: string;
}

export interface WorkflowSourceRoute extends WorkflowDetailRoute {
  sourceId: string;
}

function fixture(search: string): string {
  return new URLSearchParams(search).get("fixture") ?? "";
}

function query(value: string): string {
  if (!value) return "";
  const parameters = new URLSearchParams();
  parameters.set("fixture", value);
  return `?${parameters.toString()}`;
}

function canonicalSegment(value: string): string | null {
  try {
    const decoded = decodeURIComponent(value);
    return decoded !== "" && encodeURIComponent(decoded) === value ? decoded : null;
  } catch {
    return null;
  }
}

export const listRoute = {
  match(location: RouteLocation): WorkflowListRoute | null {
    if (location.pathname !== "/workflows" && location.pathname !== "/workflows/") return null;
    return { fixture: fixture(location.search) };
  },
  build(value: WorkflowListRoute): string {
    return `/workflows${query(value.fixture)}`;
  },
};

export const detailRoute = {
  match(location: RouteLocation): WorkflowDetailRoute | null {
    const match = /^\/workflows\/([^/]+)\/?$/.exec(location.pathname);
    if (!match) return null;
    const workflowId = canonicalSegment(match[1]);
    return workflowId === null ? null : { workflowId, fixture: fixture(location.search) };
  },
  build(value: WorkflowDetailRoute): string {
    return `/workflows/${encodeURIComponent(value.workflowId)}${query(value.fixture)}`;
  },
};

export const sourceRoute = {
  match(location: RouteLocation): WorkflowSourceRoute | null {
    const match = /^\/workflows\/([^/]+)\/sources\/([^/]+)\/?$/.exec(location.pathname);
    if (!match) return null;
    const workflowId = canonicalSegment(match[1]);
    const sourceId = canonicalSegment(match[2]);
    return workflowId === null || sourceId === null
      ? null
      : { workflowId, sourceId, fixture: fixture(location.search) };
  },
  build(value: WorkflowSourceRoute): string {
    return `/workflows/${encodeURIComponent(value.workflowId)}/sources/${encodeURIComponent(value.sourceId)}${query(value.fixture)}`;
  },
};
