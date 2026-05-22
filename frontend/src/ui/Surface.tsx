import type { HTMLAttributes } from "react";
import { cn } from "./cn";

type Width = "sm" | "md" | "lg" | "xl" | "full";

export interface SurfaceProps extends HTMLAttributes<HTMLDivElement> {
  width?: Width;
  spacing?: "sm" | "md" | "lg";
}

const widths: Record<Width, string> = {
  sm: "max-w-md",
  md: "max-w-2xl",
  lg: "max-w-4xl",
  xl: "max-w-6xl",
  full: "max-w-none",
};

const spacings = {
  sm: "py-6 md:py-10 gap-6",
  md: "py-10 md:py-16 gap-8 md:gap-12",
  lg: "py-16 md:py-24 gap-12 md:gap-16",
};

export function Surface({
  width = "lg",
  spacing = "md",
  className,
  children,
  ...rest
}: SurfaceProps) {
  return (
    <div
      className={cn(
        "mx-auto px-4 md:px-6 flex flex-col w-full",
        widths[width],
        spacings[spacing],
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  );
}
