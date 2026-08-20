export { route, type SessionsRoute } from "./route";
export { schema, type SessionsPayload } from "./data/schema";
export { request } from "./data/request";
export { polling, data } from "./data/useFeed";
export { project } from "./data/project";
export * from "./model";
export { fixtureSessions, fixtures } from "./fixtures";

export const styles = "./sessions.css";
export const loadView = () => import("./SessionsView");
