import type { RequestSpec } from "../../../shared/transport/types";
import type { SessionsRoute } from "../route";

export function request(_route: SessionsRoute): RequestSpec {
  return { url: "/api/v1/views/sessions" };
}
