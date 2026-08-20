import { catalogData, detailData, sourceData } from "./data/useFeed";
import { detailRoute, listRoute, sourceRoute } from "./route";

export * from "./model";
export * from "./route";
export { catalogData, detailData, sourceData } from "./data/useFeed";

export const list = {
  route: listRoute,
  data: catalogData,
  loadView: () => import("./view/WorkflowCatalogView"),
};

export const detail = {
  route: detailRoute,
  data: detailData,
  loadView: () => import("./view/WorkflowDetailView"),
};

export const source = {
  route: sourceRoute,
  data: sourceData,
  loadView: () => import("./view/WorkflowSourceView"),
};

export const styles = "./styles.css";
