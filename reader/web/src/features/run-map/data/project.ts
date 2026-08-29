import type { RunMapModel } from "../model";
import type { RunMapPayload } from "./schema";

export function project(payload: RunMapPayload): RunMapModel {
  return { runs: payload.runs, run: payload.run };
}
