import { useEffect, useState } from "react";

export function getHashPath(): string {
  const raw = (window.location.hash || "#/").slice(1);
  const [path] = raw.split("?");
  return path || "/";
}

/**
 * Subscribes to hashchange and returns the current path (without the query
 * string). Useful for nav active-state highlighting.
 */
export function useHashRoute(): string {
  const [path, setPath] = useState<string>(() => getHashPath());
  useEffect(() => {
    const onChange = () => setPath(getHashPath());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return path;
}
