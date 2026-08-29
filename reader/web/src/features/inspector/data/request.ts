import type { RequestSpec } from "../../../shared/transport/types";
import type { InspectorRoute } from "../route";

export function request(route: InspectorRoute): RequestSpec {
  const query = new URLSearchParams();
  query.set("run", route.run);
  query.set("ticket", route.ticket);
  const search = query.toString();
  return { url: `/api/v1/views/inspector${search ? `?${search}` : ""}` };
}
