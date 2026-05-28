import type { ReactNode } from "react";

interface Props {
  children: ReactNode;
  className?: string;
}

export function GradientGlowCard({ children, className = "" }: Props) {
  return (
    <div className={`relative ${className}`}>
      {/* Animated gradient border */}
      <div className="absolute -inset-[1px] rounded-[32px] bg-gradient-to-br from-sunbeam/30 via-leaf/20 to-nova/30 animate-gradient-shift opacity-60" />
      {/* Glow */}
      <div className="absolute -inset-4 rounded-[40px] bg-gradient-to-br from-sunbeam/10 via-leaf/10 to-nova/10 blur-2xl opacity-40" />
      {/* Content */}
      <div className="relative rounded-[32px] bg-canvas border border-ink/[0.04] p-10 md:p-16">
        {children}
      </div>
    </div>
  );
}
