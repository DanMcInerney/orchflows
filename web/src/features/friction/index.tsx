import type { ViewId } from "../../api/schema";
import { FrictionView } from "./FrictionView";

export const viewId: ViewId = "friction";
export { FrictionView, closedFrictionRecord } from "./FrictionView";
export default FrictionView;
