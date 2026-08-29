export { route, type FrictionRoute } from "./route";
export { schema, type FrictionPayload } from "./data/schema";
export { request } from "./data/request";
export { polling, data } from "./data/useFeed";
export { project } from "./data/project";
export * from "./model";
export { linkedCaptureRecord, fixtures } from "./fixtures";

export const styles = "./friction.css";
export const loadView = () => import("./FrictionView");
