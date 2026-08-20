import { useCallback, useEffect, useState } from "react";
import type { RouteLocation } from "../catalog";

function currentLocation(): RouteLocation {
  return {
    pathname: window.location.pathname,
    search: window.location.search,
    hash: window.location.hash,
  };
}

export function useBrowserLocation(): [RouteLocation, (href: string) => void] {
  const [location, setLocation] = useState(currentLocation);

  useEffect(() => {
    const changed = () => setLocation(currentLocation());
    window.addEventListener("popstate", changed);
    return () => window.removeEventListener("popstate", changed);
  }, []);

  const navigate = useCallback((href: string) => {
    window.history.pushState({}, "", href);
    setLocation(currentLocation());
  }, []);

  return [location, navigate];
}
