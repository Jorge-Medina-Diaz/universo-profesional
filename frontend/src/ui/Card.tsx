import { forwardRef, type HTMLAttributes } from "react";
import { cn } from "./cn";

type Tone = "surface" | "canvas" | "ink" | "glass";
type Padding = "sm" | "md" | "lg" | "none";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  tone?: Tone;
  padding?: Padding;
  interactive?: boolean;
  bordered?: boolean;
  as?: "div" | "section" | "article" | "li";
}

const tones: Record<Tone, string> = {
  surface: "bg-surface text-ink",
  canvas: "bg-canvas text-ink",
  ink: "bg-ink text-canvas",
  // Cosmos glass — translucent canvas + blur + hairline. The app counterpart to
  // the landing's .cos-panel; use for floating/elevated surfaces (chat,
  // inspector, featured cards) where depth should read against the backdrop.
  glass:
    "bg-[color-mix(in_srgb,var(--surface-canvas)_80%,transparent)] text-ink border border-hairline backdrop-blur-md",
};

const paddings: Record<Padding, string> = {
  none: "p-0",
  sm: "p-4",
  md: "p-6",
  lg: "p-8 md:p-10",
};

export const Card = forwardRef<HTMLDivElement, CardProps>(function Card(
  {
    tone = "surface",
    padding = "md",
    interactive = false,
    bordered = false,
    as,
    className,
    children,
    ...rest
  },
  ref,
) {
  // Treat `as` declaratively — falling back to div keeps typing simple.
  const Tag = (as ?? "div") as "div";
  return (
    <Tag
      ref={ref as never}
      className={cn(
        "rounded-card transition-all duration-280 ease-pirsch",
        tones[tone],
        paddings[padding],
        bordered && "border border-ink/8",
        interactive &&
          "cursor-pointer hover:-translate-y-[2px] hover:shadow-lift focus-within:-translate-y-[2px] focus-within:shadow-lift focus-within:ring-2 focus-within:ring-ink/20 focus-within:ring-offset-2 focus-within:outline-none",
        className,
      )}
      {...rest}
    >
      {children}
    </Tag>
  );
});
