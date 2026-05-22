/**
 * SectionLabel — editorial eyebrow with optional section number.
 *
 * Blueyard-style wayfinding: a tracked uppercase label, optionally prefixed
 * by a zero-padded index (01, 02…) set in the display serif. Use above
 * section titles to give the product a magazine-like rhythm.
 */
import type { ReactNode } from "react";
import { cn } from "./cn";

export interface SectionLabelProps {
  children: ReactNode;
  /** Zero-padded section index, e.g. 1 → "01". Omit for a plain eyebrow. */
  index?: number;
  /** Tone of the leading rule + number. */
  tone?: "ink" | "leaf" | "sunbeam" | "stone";
  className?: string;
}

const TONE_TEXT: Record<NonNullable<SectionLabelProps["tone"]>, string> = {
  ink: "text-ink",
  leaf: "text-leaf-ink",
  sunbeam: "text-sunbeam-ink",
  stone: "text-stone",
};

export function SectionLabel({
  children,
  index,
  tone = "stone",
  className,
}: SectionLabelProps) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      {index != null && (
        <span
          className={cn(
            "font-display text-[15px] leading-none tabular-nums",
            TONE_TEXT[tone],
          )}
          aria-hidden
        >
          {String(index).padStart(2, "0")}
        </span>
      )}
      <span aria-hidden className="h-px w-6 bg-hairline" />
      <span className="eyebrow">{children}</span>
    </div>
  );
}
