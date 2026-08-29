export { route, type InspectorRoute } from "./route";
export { schema, type InspectorPayload } from "./data/schema";
export { request } from "./data/request";
export { polling, data } from "./data/useFeed";
export { project } from "./data/project";
export * from "./model";
export { fixtureTicket, fixtures } from "./fixtures";

export const styles = "./inspector.css";
export const loadView = () => import("./Inspector");
