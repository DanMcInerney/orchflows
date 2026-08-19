import type { ComponentType } from "react";
import type { ExperienceSnapshot, ViewId } from "../api/schema";
import type { LocationState } from "../state/location";

export interface ViewProps { snapshot: ExperienceSnapshot; location: LocationState }
export interface ViewModule { viewId: ViewId; default: ComponentType<ViewProps> }

const modules = import.meta.glob<ViewModule>("../views/*.tsx", { eager: true });

export function registeredViews(): Partial<Record<ViewId, ComponentType<ViewProps>>> {
  const registered: Partial<Record<ViewId, ComponentType<ViewProps>>> = {};
  for (const module of Object.values(modules)) registered[module.viewId] = module.default;
  return registered;
}
