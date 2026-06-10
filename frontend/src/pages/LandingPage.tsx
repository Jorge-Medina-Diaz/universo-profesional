import { useTranslation } from "react-i18next";

import { SiteNav } from "@/landing/components/SiteNav";
import { registerLandingI18n } from "@/landing/i18n";
import { AgentPilot } from "@/landing/sections/AgentPilot";
import { Closing } from "@/landing/sections/Closing";
import { EngineRoom } from "@/landing/sections/EngineRoom";
import { ExploitOffer } from "@/landing/sections/ExploitOffer";
import { FeedTheUniverse } from "@/landing/sections/FeedTheUniverse";
import { Hero } from "@/landing/sections/Hero";
import { Manifesto } from "@/landing/sections/Manifesto";
import { McpNative } from "@/landing/sections/McpNative";
import { Trust } from "@/landing/sections/Trust";
import { TwinLive } from "@/landing/sections/TwinLive";

registerLandingI18n();

/**
 * The landing — one claim, three proofs, one ask (see plan: landing redesign).
 *
 * Arc: hero (the claim) → manifesto (the enemy) → FEED (talk, graph grows) →
 * EXPLOIT (offer → evidence-backed CV) → TWIN (live, production endpoint) →
 * agent-native (the app, piloted) → engine room (reproducible facts) → MCP →
 * trust mechanisms → pricing + close. Two deep-space bands (twin, engine);
 * nova appears only where the agent acts.
 */
export function LandingPage() {
  const { t } = useTranslation("landing");

  return (
    <div className="landing-cosmos min-h-screen">
      <SiteNav />
      <main>
        <Hero />
        <Manifesto />
        <FeedTheUniverse />
        <ExploitOffer />
        <TwinLive />
        <AgentPilot />
        <EngineRoom />
        <McpNative />
        <Trust />
        <Closing />
      </main>

      <footer className="border-t border-[var(--cos-hairline)] py-14">
        <div className="mx-auto max-w-6xl px-5 md:px-8">
          <div className="flex flex-col items-center justify-between gap-6 md:flex-row">
            <div className="flex items-center gap-2.5">
              <span className="relative grid h-6 w-6 place-items-center">
                <span className="absolute h-2 w-2 rounded-full bg-[#ffda6e] shadow-[0_0_12px_2px_rgba(255,218,110,0.6)]" />
                <span className="absolute h-6 w-6 rounded-full border border-[var(--cos-hairline)]" />
              </span>
              <span className="cos-display text-base text-[var(--cos-ink)]">
                Universo Profesional
              </span>
            </div>
            <div className="flex items-center gap-6 text-sm text-[var(--cos-stone)]">
              <a href="#/legal/privacy" className="transition-colors hover:text-[var(--cos-ink)]">
                {t("footer.privacy")}
              </a>
              <a href="#/legal/terms" className="transition-colors hover:text-[var(--cos-ink)]">
                {t("footer.terms")}
              </a>
              <a href="#/mcp" className="transition-colors hover:text-[var(--cos-ink)]">
                {t("footer.mcpDocs")}
              </a>
              <a href="#/t/demo" className="transition-colors hover:text-[var(--cos-ink)]">
                {t("footer.demo")}
              </a>
            </div>
            <p className="text-xs text-[var(--cos-faint)]">
              © {new Date().getFullYear()} Universo Profesional
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
