import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { cn } from "./cn";

type Variant = "primary" | "secondary" | "ghost" | "outline" | "danger";
type Size = "sm" | "md" | "lg";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  leadingIcon?: ReactNode;
  trailingIcon?: ReactNode;
  fullWidth?: boolean;
}

const base =
  "inline-flex items-center justify-center gap-2 font-medium select-none transition-all duration-180 ease-pirsch disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/30 focus-visible:ring-offset-2 focus-visible:ring-offset-canvas";

const sizes: Record<Size, string> = {
  sm: "h-9 px-4 text-sm rounded-btn",
  md: "h-11 px-6 text-sm rounded-btn",
  lg: "h-12 px-8 text-base rounded-btn",
};

const variants: Record<Variant, string> = {
  primary:
    "bg-sunbeam text-ink hover:bg-[#ffcf45] hover:-translate-y-[1px] active:translate-y-0 shadow-soft",
  secondary:
    "bg-leaf text-ink hover:bg-[#5cc28d] hover:-translate-y-[1px] active:translate-y-0 shadow-soft",
  ghost: "bg-transparent text-ink hover:bg-black/5",
  outline:
    "bg-transparent text-ink border border-ink/15 hover:bg-black/5 hover:border-ink/30",
  danger: "bg-red-500 text-white hover:bg-red-600",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = "primary",
    size = "md",
    loading = false,
    leadingIcon,
    trailingIcon,
    fullWidth,
    className,
    children,
    disabled,
    ...rest
  },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(base, sizes[size], variants[variant], fullWidth && "w-full", className)}
      {...rest}
    >
      {loading ? (
        <Spinner />
      ) : (
        leadingIcon && <span className="inline-flex shrink-0">{leadingIcon}</span>
      )}
      <span className="truncate">{children}</span>
      {!loading && trailingIcon && (
        <span className="inline-flex shrink-0">{trailingIcon}</span>
      )}
    </button>
  );
});

function Spinner() {
  return (
    <svg
      aria-hidden
      className="animate-spin h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeOpacity="0.25"
        strokeWidth="3"
      />
      <path
        d="M22 12a10 10 0 0 1-10 10"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}
