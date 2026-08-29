import { frictionModel, type FrictionModel } from "../model";
import type { FrictionPayload } from "./schema";

export function project(payload: FrictionPayload): FrictionModel {
  return frictionModel(payload.friction);
}
