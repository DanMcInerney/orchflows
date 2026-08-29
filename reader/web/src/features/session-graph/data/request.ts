import type { RequestSpec } from "../../../shared/transport/types";
import type { SessionGraphRoute } from "../route";

export function request(route: SessionGraphRoute): RequestSpec {
  const query = new URLSearchParams({ session: route.session });
  return { url: `/api/v1/views/session-graph?${query.toString()}` };
}
