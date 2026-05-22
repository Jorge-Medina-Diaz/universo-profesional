import type { HTMLAttributes } from "react";
import { cn } from "./cn";

export interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  /** Tailwind sizing utilities (e.g. "h-6 w-32"). */
  className?: string;
  /** Shape: "text" = subtle radius, "block" = card radius, "circle" = full round. */
  shape?: "text" | "block" | "circle";
}

/**
 * Skeleton loading placeholder. Uses a soft pulse so it doesn't fight with
 * other entry animations. Match the geometry of the final content to avoid
 * layout shift on swap.
 */
export function Skeleton({ className, shape = "text", ...rest }: SkeletonProps) {
  return (
    <div
      aria-hidden
      className={cn(
        "bg-black/[0.04] animate-pulse",
        shape === "text" && "rounded",
        shape === "block" && "rounded-card",
        shape === "circle" && "rounded-full",
        className,
      )}
      {...rest}
    />
  );
}

/** Pre-baked skeleton for the most common "page-loading" affordance. */
export function PageSkeleton() {
  return (
    <div className="flex flex-col gap-4 max-w-3xl mx-auto px-4 py-12">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-9 w-2/3" />
      <Skeleton className="h-4 w-3/4" />
      <div className="grid md:grid-cols-3 gap-4 pt-6">
        <Skeleton shape="block" className="h-32" />
        <Skeleton shape="block" className="h-32" />
        <Skeleton shape="block" className="h-32" />
      </div>
    </div>
  );
}
