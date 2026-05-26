import { cn } from "./cn";

export interface ShimmerSkeletonProps {
  className?: string;
  count?: number;
}

/**
 * Skeleton loader with a horizontal shimmer sweep animation.
 * Replaces generic `animate-pulse` with a more polished loading state.
 */
export function ShimmerSkeleton({ className, count = 1 }: ShimmerSkeletonProps) {
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="shimmer rounded-btn h-4 w-full"
          aria-hidden="true"
        />
      ))}
    </div>
  );
}
