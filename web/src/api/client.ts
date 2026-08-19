import { isExperienceSnapshot, type ExperienceSnapshot } from "./schema";
import type { LocationState } from "../state/location";

export function experienceUrl(location: LocationState): string {
  const query = new URLSearchParams({ view: location.view });
  if (location.run) query.set("run", location.run);
  if (location.ticket) query.set("ticket", location.ticket);
  if (location.session) query.set("session", location.session);
  return `/api/v1/experience?${query.toString()}`;
}

export async function readExperience(
  location: LocationState,
  etag: string | null
): Promise<{ snapshot: ExperienceSnapshot | null; etag: string | null }> {
  const headers = etag ? { "If-None-Match": etag } : undefined;
  const response = await fetch(experienceUrl(location), { headers, cache: "no-store" });
  const nextTag = response.headers.get("ETag") ?? etag;
  if (response.status === 304) return { snapshot: null, etag: nextTag };
  if (!response.ok) throw new Error("reader response was not successful");
  const value: unknown = await response.json();
  if (!isExperienceSnapshot(value)) throw new Error("reader response shape was invalid");
  return { snapshot: value, etag: nextTag };
}
