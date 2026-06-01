import type { ReactNode } from "react";
import { cn } from "./cn";

/**
 * ProgressRing — one canonical 0-100 ring.
 *
 * Replaces the two bespoke SVG gauges that had drifted apart
 * (ProfileCompleteness.CompletenessGauge @ 100×100 r=38, and the inline ring in
 * DiscoveryProgress @ viewBox 36 w-16). Colour follows a single threshold scale
 * (leaf ≥80 · sunbeam ≥50 · stone) using theme-aware tokens, so it reads
 * correctly in light and dark. Center content is provided via `children`.
 */
export interface ProgressRingProps {
  /** 0..100; clamped. */
  value: number;
  /** Outer diameter in px. */
  size?: number;
  strokeWidth?: number;
  className?: string;
  children?: ReactNode;
  ariaLabel?: string;
}

function toneColor(v: number): string {
  if (v >= 80) return "var(--color-leafy-green)";
  if (v >= 50) return "var(--color-sunbeam-yellow)";
  return "var(--color-muted-stone)";
}

export function ProgressRing({
  value,
  size = 48,
  strokeWidth = 4,
  className,
  children,
  ariaLabel,
}: ProgressRingProps) {
  const v = Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
  const r = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - v / 100);

  return (
    <div
      className={cn("relative inline-grid place-items-center shrink-0", className)}
      style={{ width: size, height: size }}
      role="img"
      aria-label={ariaLabel ?? `${Math.round(v)}% completo`}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="-rotate-90"
        aria-hidden
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--hairline)"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={toneColor(v)}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 600ms var(--ease-pirsch)" }}
        />
      </svg>
      {children != null && (
        <div className="absolute inset-0 grid place-items-center">{children}</div>
      )}
    </div>
  );
}
