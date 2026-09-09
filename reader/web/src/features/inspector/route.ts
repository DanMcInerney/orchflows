import {
  executionTicketRoute,
  type ExecutionTicketRoute,
  type RouteLocation,
} from "../../shared/routes/executionRoutes";

export interface InspectorRoute extends ExecutionTicketRoute {
  tab?: string;
}

// The inspector owns its tab query; the shared route owns ticket identity.
export const route = {
  match(location: RouteLocation): InspectorRoute | null {
    const ticket = executionTicketRoute.match(location);
    if (!ticket) return null;
    const tab = new URLSearchParams(location.search).get("tab");
    return tab ? { ...ticket, tab } : ticket;
  },
  build(value: InspectorRoute): string {
    const href = executionTicketRoute.build(value);
    if (!value.tab) return href;
    return `${href}${href.includes("?") ? "&" : "?"}${new URLSearchParams({ tab: value.tab })}`;
  },
};
