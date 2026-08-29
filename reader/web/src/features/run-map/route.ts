import {
  executionRunRoute,
  type ExecutionRunRoute,
  type RouteLocation,
} from "../../shared/routes/executionRoutes";

export type RunMapRoute = ExecutionRunRoute;

export const route = {
  match(location: RouteLocation): RunMapRoute | null {
    return executionRunRoute.match(location);
  },
  build(value: RunMapRoute): string {
    return executionRunRoute.build(value);
  },
};
