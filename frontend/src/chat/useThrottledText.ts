/**
 * Throttled text stream hook.
 *
 * Batches rapid token-stream updates so React only re-renders every `ms`
 * instead of on every token. Eliminates jank on long assistant replies.
 */
import { useState, useEffect, useRef, useCallback } from "react";

export function useThrottledText(raw: string, ms = 50) {
  const [displayed, setDisplayed] = useState(raw);
  const pendingRef = useRef(raw);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastFlushRef = useRef(0);

  const flush = useCallback(() => {
    timerRef.current = null;
    lastFlushRef.current = performance.now();
    setDisplayed(pendingRef.current);
  }, []);

  useEffect(() => {
    pendingRef.current = raw;
    if (timerRef.current) return;
    const sinceLast = performance.now() - lastFlushRef.current;
    const delay = Math.max(0, ms - sinceLast);
    timerRef.current = setTimeout(flush, delay);
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [raw, ms, flush]);

  // Ensure final text is always flushed even if unmounted mid-timer.
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, []);

  return displayed;
}
