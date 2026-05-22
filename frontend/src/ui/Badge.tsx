import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "./cn";

type Tone = "leaf" | "sunbeam" | "stone" | "ink" | "amber" | "danger";
type Size = "sm" | "md";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
  size?: Size;
  dot?: boolean;
  icon?: ReactNode;
}

const tones: Record<Tone, string> = {
  leaf: "bg-leaf-soft text-leaf-ink",
  sunbeam: "bg-sunbeam-soft text-sunbeam-ink",
  stone: "bg-black/[0.04] text-stone",
  ink: "bg-ink text-canvas",
  amber: "bg-amber-100 text-amber-900",
  danger: "bg-red-50 text-red-700",
};

const dotColors: Record<Tone, string> = {
  leaf: "bg-leaf",
  sunbeam: "bg-sunbeam",
  stone: "bg-stone",
  ink: "bg-canvas",
  amber: "bg-amber-500",
  danger: "bg-red-500",
};

const sizes: Record<Size, string> = {
  sm: "text-[11px] px-2 py-0.5 gap-1",
  md: "text-xs px-3 py-1 gap-1.5",
};

export function Badge({
  tone = "leaf",
  size = "md",
  dot,
  icon,
  className,
  children,
  ...rest
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-tag font-medium leading-none whitespace-nowrap",
        tones[tone],
        sizes[size],
        className,
      )}
      {...rest}
    >
      {dot && <span aria-hidden className={cn("inline-block w-1.5 h-1.5 rounded-full", dotColors[tone])} />}
      {icon && <span aria-hidden className="inline-flex">{icon}</span>}
      {children}
    </span>
  );
}
