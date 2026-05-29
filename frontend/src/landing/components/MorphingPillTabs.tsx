import { motion } from "motion/react";

interface Tab {
  id: string;
  label: string;
}

interface Props {
  tabs: Tab[];
  active: string;
  onChange: (id: string) => void;
}

export function MorphingPillTabs({ tabs, active, onChange }: Props) {
  return (
    <div className="inline-flex items-center gap-1 p-1.5 rounded-full bg-[var(--cos-fill-strong)] border border-[var(--cos-hairline)]">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className="relative px-5 py-2 text-sm font-medium rounded-full transition-colors duration-200 z-10"
          style={{
            color: active === tab.id ? "var(--cos-ink)" : "var(--cos-stone)",
          }}
        >
          {active === tab.id && (
            <motion.div
              layoutId="pill-indicator"
              className="absolute inset-0 bg-[var(--cos-panel-raised)] rounded-full shadow-soft border border-[var(--cos-hairline)]"
              style={{ zIndex: -1 }}
              transition={{ type: "spring", damping: 28, stiffness: 320 }}
            />
          )}
          {tab.label}
        </button>
      ))}
    </div>
  );
}
