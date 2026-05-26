import { useState, type ReactNode } from "react";
import { motion } from "framer-motion";
import { cn } from "./cn";

export interface Tab {
  id: string;
  label: ReactNode;
  content: ReactNode;
  disabled?: boolean;
}

export interface TabsProps {
  tabs: Tab[];
  defaultTab?: string;
  className?: string;
  tabListClassName?: string;
  tabPanelClassName?: string;
  onChange?: (id: string) => void;
}

export function Tabs({
  tabs,
  defaultTab,
  className,
  tabListClassName,
  tabPanelClassName,
  onChange,
}: TabsProps) {
  const [active, setActive] = useState(defaultTab ?? tabs[0]?.id);
  const activeTab = tabs.find((t) => t.id === active) ?? tabs[0];

  const handleSelect = (id: string) => {
    setActive(id);
    onChange?.(id);
  };

  return (
    <div className={cn("w-full", className)}>
      <div
        role="tablist"
        className={cn(
          "relative flex items-center gap-1 border-b border-ink/10",
          tabListClassName,
        )}
      >
        {tabs.map((tab) => {
          const isActive = tab.id === active;
          return (
            <button
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              aria-controls={`tabpanel-${tab.id}`}
              id={`tab-${tab.id}`}
              disabled={tab.disabled}
              onClick={() => handleSelect(tab.id)}
              className={cn(
                "relative px-4 py-2.5 text-sm font-medium transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/20 rounded-t-lg",
                isActive ? "text-ink" : "text-stone hover:text-ink/80",
                tab.disabled && "opacity-40 cursor-not-allowed",
              )}
            >
              {tab.label}
              {isActive && (
                <motion.div
                  layoutId="tabs-indicator"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-sunbeam rounded-full"
                  transition={{ type: "spring", damping: 30, stiffness: 400 }}
                />
              )}
            </button>
          );
        })}
      </div>

      <div
        role="tabpanel"
        id={`tabpanel-${activeTab?.id}`}
        aria-labelledby={`tab-${activeTab?.id}`}
        className={cn("pt-4", tabPanelClassName)}
      >
        {activeTab?.content}
      </div>
    </div>
  );
}
