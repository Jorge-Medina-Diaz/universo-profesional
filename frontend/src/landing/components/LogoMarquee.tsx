import { Link, GitMerge, Brain, Terminal, Globe, FileJson, Code2 } from "lucide-react";

const LOGOS = [
  { name: "Claude", icon: Brain },
  { name: "Cursor", icon: Terminal },
  { name: "VS Code", icon: Code2 },
  { name: "LinkedIn", icon: Link },
  { name: "GitHub", icon: GitMerge },
  { name: "ESCO (UE)", icon: Globe },
  { name: "JSON Resume", icon: FileJson },
];

export function LogoMarquee() {
  const items = [...LOGOS, ...LOGOS, ...LOGOS];

  return (
    <section className="overflow-hidden border-y border-[var(--cos-hairline)] py-10">
      <p className="mb-7 text-center text-[11px] uppercase tracking-[0.2em] text-[var(--cos-faint)]">
        Funciona con tu mundo
      </p>
      <div className="cos-marquee-mask relative flex overflow-hidden">
        <div className="flex shrink-0 motion-safe:animate-marquee items-center gap-12 px-6">
          {items.map((item, i) => (
            <div
              key={`${item.name}-${i}`}
              className="flex shrink-0 items-center gap-2.5 text-[var(--cos-faint)] transition-colors duration-300 hover:text-[var(--cos-ink)]"
            >
              <item.icon size={18} strokeWidth={1.5} />
              <span className="whitespace-nowrap text-sm font-medium">{item.name}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
