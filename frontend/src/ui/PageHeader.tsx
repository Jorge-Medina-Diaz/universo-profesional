import type { ReactNode } from "react";
import { Reveal } from "./motion/Reveal";
import { cn } from "./cn";

export interface PageHeaderProps {
  eyebrow?: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  align?: "left" | "center";
  className?: string;
}

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  actions,
  align = "left",
  className,
}: PageHeaderProps) {
  const centered = align === "center";
  return (
    <header
      className={cn(
        "flex flex-col gap-4 md:flex-row md:items-end md:justify-between",
        centered && "items-center text-center md:flex-col md:items-center",
        className,
      )}
    >
      <div className={cn("flex flex-col gap-2", centered && "items-center")}>
        {eyebrow && (
          <Reveal delay={0}>
            <span className="eyebrow">{eyebrow}</span>
          </Reveal>
        )}
        <Reveal delay={0.04}>
          <h1
            className={cn(
              "font-display text-[34px] md:text-heading-lg lg:text-[44px] leading-[1.04] text-ink",
            )}
          >
            {title}
          </h1>
        </Reveal>
        {subtitle && (
          <Reveal delay={0.08}>
            <p className="text-base md:text-body-lg text-stone max-w-2xl">{subtitle}</p>
          </Reveal>
        )}
      </div>
      {actions && (
        <Reveal delay={0.12} className="flex flex-wrap gap-2 shrink-0">
          {actions}
        </Reveal>
      )}
    </header>
  );
}
