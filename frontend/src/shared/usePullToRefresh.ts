import { useEffect, useRef, useState, useCallback } from "react";

const THRESHOLD = 80;
const MAX_PULL = 120;

/**
 * Mobile pull-to-refresh hook. When the user pulls down while scrolled to
 * the top, `onRefresh` is fired. Returns `pulling` and `pullProgress` so the
 * caller can render a visual indicator.
 *
 * Only activates on touch devices; on desktop it is a no-op.
 */
export function usePullToRefresh(onRefresh: () => void, enabled = true) {
  const [pulling, setPulling] = useState(false);
  const [progress, setProgress] = useState(0);
  const startY = useRef(0);
  const triggered = useRef(false);

  const reset = useCallback(() => {
    setPulling(false);
    setProgress(0);
    triggered.current = false;
  }, []);

  useEffect(() => {
    if (!enabled || "ontouchstart" in window === false) return;

    const onTouchStart = (e: TouchEvent) => {
      if (window.scrollY > 5) return;
      startY.current = e.touches[0].clientY;
      triggered.current = false;
    };

    const onTouchMove = (e: TouchEvent) => {
      if (window.scrollY > 5) {
        if (pulling) reset();
        return;
      }
      const y = e.touches[0].clientY;
      const delta = y - startY.current;
      if (delta > 0) {
        setPulling(true);
        const p = Math.min(delta / THRESHOLD, 1);
        setProgress(p);
        if (delta > MAX_PULL && !triggered.current) {
          triggered.current = true;
          onRefresh();
          // Keep the indicator visible briefly
          setTimeout(reset, 600);
        }
      }
    };

    const onTouchEnd = () => {
      if (pulling && !triggered.current) {
        reset();
      }
    };

    window.addEventListener("touchstart", onTouchStart, { passive: true });
    window.addEventListener("touchmove", onTouchMove, { passive: true });
    window.addEventListener("touchend", onTouchEnd, { passive: true });

    return () => {
      window.removeEventListener("touchstart", onTouchStart);
      window.removeEventListener("touchmove", onTouchMove);
      window.removeEventListener("touchend", onTouchEnd);
    };
  }, [enabled, onRefresh, pulling, reset]);

  return { pulling, progress };
}
