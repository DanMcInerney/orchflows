import { useEffect, useState } from "react";
import { readExperience } from "./api/client";
import type { ExperienceSnapshot } from "./api/schema";
import type { LocationState } from "./state/location";

const ACTIVE_DELAY_MS = 750;
const IDLE_DELAY_MS = 2_500;

export function useExperienceFeed(location: LocationState): {
  snapshot: ExperienceSnapshot | null;
  unavailable: boolean;
} {
  const [snapshot, setSnapshot] = useState<ExperienceSnapshot | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let etag: string | null = null;
    let timer: number | undefined;
    let active = true;
    const poll = async () => {
      try {
        const result = await readExperience(location, etag);
        etag = result.etag;
        if (result.snapshot) {
          active = Boolean(result.snapshot.run?.active);
          if (!cancelled) setSnapshot(result.snapshot);
        }
        if (!cancelled) setUnavailable(false);
      } catch {
        if (!cancelled) setUnavailable(true);
      } finally {
        if (!cancelled) timer = window.setTimeout(poll, active ? ACTIVE_DELAY_MS : IDLE_DELAY_MS);
      }
    };
    void poll();
    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [location.view, location.run, location.ticket, location.session]);

  return { snapshot, unavailable };
}
