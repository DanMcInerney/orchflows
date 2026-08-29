import type { RequestSpec } from "../../../shared/transport/types";
import type { NowRoute } from "../route";

export function request(_route: NowRoute): RequestSpec {
  return { url: "/api/v1/views/now" };
}
