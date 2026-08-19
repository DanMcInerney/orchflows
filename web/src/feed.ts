import { useEffect, useState } from "react";

import { isObserveSnapshot, type ObserveSnapshot } from "./model";

const ACTIVE_DELAY_MS = 750;
const IDLE_DELAY_MS = 2_500;

function feedUrl(): string {
  return `/api/observe${window.location.search}`;
}

export function useObserveFeed(): { snapshot: ObserveSnapshot | null; unavailable: boolean } {
  const [snapshot, setSnapshot] = useState<ObserveSnapshot | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let etag: string | null = null;
    let timer: number | undefined;
    let active = true;

    const poll = async () => {
      const headers = etag ? { "If-None-Match": etag } : undefined;
      try {
        const response = await fetch(feedUrl(), { headers, cache: "no-store" });
        const seen = response.headers.get("ETag");
        if (seen) etag = seen;
        if (response.status !== 304) {
          if (!response.ok) throw new Error("reader response was not successful");
          const candidate: unknown = await response.json();
          if (!isObserveSnapshot(candidate)) throw new Error("reader response shape was invalid");
          active = candidate.active;
          if (!cancelled) setSnapshot(candidate);
        }
        if (!cancelled) setUnavailable(false);
      } catch {
        if (!cancelled) setUnavailable(true);
      } finally {
        if (!cancelled) {
          timer = window.setTimeout(poll, active ? ACTIVE_DELAY_MS : IDLE_DELAY_MS);
        }
      }
    };

    void poll();
    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, []);

  return { snapshot, unavailable };
}
