import type { ReactNode } from "react";
import { cn } from "./cn";

export interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  secondaryAction?: ReactNode;
  className?: string;
}

/**
 * Standard empty-state card used across list pages (Documents, Jobs, Notes,
 * Billing, MCP, etc.). Keeps the layout from feeling broken when there is no
 * data yet.
 */
export function EmptyState({
  icon,
  title,
  description,
  action,
  secondaryAction,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "text-center space-y-4 py-10 px-6",
        className,
      )}
    >
      <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-surface text-stone">
        {icon}
      </div>
      <h3 className="text-heading-sm font-medium tracking-tight">{title}</h3>
      {description && (
        <p className="text-sm text-stone max-w-md mx-auto">{description}</p>
      )}
      {(action || secondaryAction) && (
        <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
          {action}
          {secondaryAction}
        </div>
      )}
    </div>
  );
}
