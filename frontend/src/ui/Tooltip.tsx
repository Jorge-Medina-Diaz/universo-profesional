import { useState, type ReactNode } from "react";
import { cn } from "./cn";

export interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  className?: string;
  delay?: number;
}

/**
 * Simple tooltip with CSS-only delay.
 * For more complex cases, consider Radix UI Tooltip.
 */
export function Tooltip({ content, children, className, delay = 400 }: TooltipProps) {
  const [show, setShow] = useState(false);
  let timer: ReturnType<typeof setTimeout>;

  return (
    <div
      className="relative inline-flex"
      onMouseEnter={() => {
        timer = setTimeout(() => setShow(true), delay);
      }}
      onMouseLeave={() => {
        clearTimeout(timer);
        setShow(false);
      }}
    >
      {children}
      {show && (
        <div
          className={cn(
            "absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2",
            "rounded-input border border-hairline bg-canvas px-3 py-1.5 text-xs text-ink shadow-soft",
            "animate-in fade-in duration-180",
            className,
          )}
        >
          {content}
          <span className="absolute left-1/2 top-full -translate-x-1/2 -translate-y-1/2 rotate-45 border-r border-b border-hairline bg-canvas p-1" />
        </div>
      )}
    </div>
  );
}
