import {
  executionRunRoute,
  type ExecutionRunRoute,
  type RouteLocation,
} from "../../shared/routes/executionRoutes";

export interface RunMapRoute extends ExecutionRunRoute {
  /** Optional Now-page scope: a comma-joined ticket-id set to focus in the canonical graph. */
  group?: string;
}

export const route = {
  match(location: RouteLocation): RunMapRoute | null {
    const matched = executionRunRoute.match(location);
    if (!matched) return null;
    const group = new URLSearchParams(location.search).get("group");
    return group ? { ...matched, group } : matched;
  },
  build(value: RunMapRoute): string {
    const base = executionRunRoute.build(value);
    if (!value.group) return base;
    const [path, search] = base.split("?");
    const params = new URLSearchParams(search ?? "");
    params.set("group", value.group);
    return `${path}?${params.toString()}`;
  },
};
