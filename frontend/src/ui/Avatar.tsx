import { cn } from "./cn";

export interface AvatarProps {
  src?: string | null;
  name?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

/**
 * Avatar with image fallback to initials.
 */
export function Avatar({ src, name = "", size = "md", className }: AvatarProps) {
  const initial = (name[0] ?? "?").toUpperCase();

  const sizeClasses = {
    sm: "h-8 w-8 text-xs",
    md: "h-10 w-10 text-sm",
    lg: "h-14 w-14 text-lg",
  };

  return (
    <div
      className={cn(
        "relative inline-flex items-center justify-center rounded-full bg-surface font-semibold text-ink overflow-hidden",
        sizeClasses[size],
        className,
      )}
    >
      {src ? (
        <img src={src} alt={name} className="h-full w-full object-cover" />
      ) : (
        <span>{initial}</span>
      )}
    </div>
  );
}
