import type { RequestSpec } from "../../../shared/transport/types";
import type { FrictionRoute } from "../route";

export function request(_route: FrictionRoute): RequestSpec {
  return { url: "/api/v1/views/friction" };
}
