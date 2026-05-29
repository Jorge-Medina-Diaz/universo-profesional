import { useEffect, useState, useRef } from "react";
import { motion } from "motion/react";

interface Props {
  value: number;
  suffix?: string;
  prefix?: string;
  label: string;
  duration?: number;
  accent?: string;
}

function useCountUp(target: number, duration = 2000, trigger = true) {
  const [count, setCount] = useState(0);
  const frameRef = useRef<number>(0);
  const startRef = useRef<number>(0);

  useEffect(() => {
    if (!trigger) return;
    // Respect reduced-motion: jump straight to the target, skip the rAF loop.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setCount(target);
      return;
    }
    startRef.current = performance.now();
    const step = (now: number) => {
      const elapsed = now - startRef.current;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.floor(eased * target));
      if (progress < 1) frameRef.current = requestAnimationFrame(step);
    };
    frameRef.current = requestAnimationFrame(step);
    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, [target, duration, trigger]);

  return count;
}

export function FloatingStat({
  value,
  suffix = "",
  prefix = "",
  label,
  duration = 2000,
  accent = "var(--cos-ink)",
}: Props) {
  const [inView, setInView] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setInView(true);
      },
      { threshold: 0.3 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  const count = useCountUp(value, duration, inView);

  return (
    <motion.div
      ref={ref}
      className="text-center"
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5 }}
    >
      <div
        className="cos-display mb-1 text-4xl tabular-nums tracking-tight md:text-5xl"
        style={{ color: accent }}
      >
        {prefix}
        {count.toLocaleString()}
        {suffix}
      </div>
      <div className="text-sm text-[var(--cos-stone)]">{label}</div>
    </motion.div>
  );
}
