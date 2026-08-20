export { route, type NowRoute } from "./route";
export { schema, type NowPayload } from "./data/schema";
export { request } from "./data/request";
export { polling, data } from "./data/useFeed";
export { project } from "./data/project";
export * from "./model";
export { model } from "./model";
export { nowFixture, fixtures } from "./fixtures";

export const styles = "./now.css";
export const loadView = () => import("./NowView");
