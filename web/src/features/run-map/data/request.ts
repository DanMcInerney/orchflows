import type { RequestSpec } from "../../../shared/transport/types";
import type { RunMapRoute } from "../route";

export function request(route: RunMapRoute): RequestSpec {
  const query = new URLSearchParams();
  if (!route.fixture && route.run) query.set("run", route.run);
  const search = query.toString();
  return { url: `/api/v1/views/run-map${search ? `?${search}` : ""}` };
}
