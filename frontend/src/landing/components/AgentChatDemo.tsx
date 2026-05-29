import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Check, X } from "lucide-react";

const TABS = [
  { id: "healthcare", label: "Sanidad" },
  { id: "creative", label: "Creativos" },
  { id: "business", label: "Negocios" },
  { id: "education", label: "Educación" },
];

const MESSAGES: Record<string, { from: "user" | "agent" | "card"; text: string; entity?: string }[]> = {
  healthcare: [
    { from: "user", text: "Añade mi experiencia como enfermera en urgencias" },
    { from: "agent", text: "He detectado una nueva experiencia. ¿La añado al universo?" },
    { from: "card", text: "Confirmar adición", entity: "Enfermera Urgencias @ Hospital General" },
    { from: "user", text: "Sí, confirma" },
    { from: "agent", text: "Experiencia añadida. He vinculado 5 skills y actualizado tu grafo." },
  ],
  creative: [
    { from: "user", text: "Genera una carta para la oferta de arquitecto sostenible" },
    { from: "agent", text: "Analizando la oferta y tu perfil... Encontré 3 proyectos relevantes." },
    { from: "card", text: "Carta lista", entity: "Arquitecto Sostenible — GreenBuild" },
    { from: "user", text: "Descárgala en PDF" },
    { from: "agent", text: "Carta generada. Destacé tu certificación LEED y el proyecto Bioclimático." },
  ],
  business: [
    { from: "user", text: "¿Qué skills me faltan para ser directora de marketing?" },
    { from: "agent", text: "Comparando tu perfil con 12 ofertas de Director de Marketing..." },
    { from: "card", text: "Análisis completado", entity: "3 habilidades prioritarias detectadas" },
    { from: "user", text: "Cuéntame más" },
    { from: "agent", text: "Analytics avanzado, Growth hacking y Liderazgo cross-funcional. ¿Quieres un plan?" },
  ],
  education: [
    { from: "user", text: "Añade mi máster en innovación educativa" },
    { from: "agent", text: "Detecté el máster. También encontré 2 publicaciones relacionadas. ¿Las añado?" },
    { from: "card", text: "Confirmar publicaciones", entity: "2 papers sobre didáctica STEM" },
    { from: "user", text: "Sí, añádelas" },
    { from: "agent", text: "Perfecto. Tu perfil docente ahora incluye el máster y las publicaciones vinculadas." },
  ],
};

export function AgentChatDemo() {
  const [tab, setTab] = useState("healthcare");
  const [msgIdx, setMsgIdx] = useState(0);
  const [showTyping, setShowTyping] = useState(false);

  const messages = MESSAGES[tab];

  useEffect(() => {
    setMsgIdx(0);
  }, [tab]);

  useEffect(() => {
    if (msgIdx >= messages.length) return;
    const isAgent = messages[msgIdx].from === "agent";
    if (isAgent) {
      setShowTyping(true);
      const t = setTimeout(() => setShowTyping(false), 900);
      return () => clearTimeout(t);
    }
  }, [msgIdx, tab, messages]);

  useEffect(() => {
    if (msgIdx >= messages.length) {
      const t = setTimeout(() => setMsgIdx(0), 3000);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setMsgIdx((i) => i + 1), 2200);
    return () => clearTimeout(t);
  }, [msgIdx, tab, messages.length]);

  const visible = messages.slice(0, msgIdx + 1);

  return (
    <section className="py-32 md:py-40 bg-[var(--cos-bg-2)] overflow-hidden">
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center mb-16">
          <h2 className="font-display text-[var(--cos-ink)] text-4xl md:text-6xl leading-[1.05] tracking-tight mb-6">
            Habla con tu
            <br />
            <span className="text-[var(--cos-stone)]">carrera.</span>
          </h2>
          <p className="text-lg text-[var(--cos-stone)] max-w-md mx-auto">
            En lenguaje natural. Sin formularios. Sin plantillas.
          </p>
        </div>

        {/* Tabs */}
        <div className="flex justify-center gap-2 mb-12">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 ${
                t.id === tab
                  ? "bg-[var(--cos-ink)] text-[var(--cos-on-ink)]"
                  : "text-[var(--cos-stone)] hover:text-[var(--cos-ink)] hover:bg-[var(--cos-fill)]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Chat mockup */}
        <div className="max-w-lg mx-auto">
          <div className="rounded-2xl border border-[var(--cos-hairline)] bg-[var(--cos-panel)] overflow-hidden">
            {/* Header */}
            <div className="flex items-center gap-2 px-5 py-3 border-b border-[var(--cos-hairline)]">
              <div className="w-2 h-2 rounded-full bg-[var(--cos-nova)] animate-pulse" />
              <span className="text-xs text-[var(--cos-stone)]">Agente MCP activo</span>
            </div>

            {/* Messages */}
            <div className="p-5 space-y-3 min-h-[280px]">
              <AnimatePresence mode="popLayout">
                {visible.map((msg, i) => (
                  <motion.div
                    key={`${tab}-${i}`}
                    layout
                    initial={{ opacity: 0, y: 10, scale: 0.96 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.96 }}
                    transition={{ duration: 0.3 }}
                    className={`flex ${msg.from === "user" ? "justify-end" : "justify-start"}`}
                  >
                    {msg.from === "card" ? (
                      <div className="bg-[var(--cos-panel-raised)] border border-[var(--cos-hairline)] rounded-xl p-4 max-w-[85%] shadow-sm">
                        <div className="text-[11px] text-[var(--cos-stone)] mb-1">{msg.text}</div>
                        <div className="text-sm font-medium text-[var(--cos-ink)] mb-3">{msg.entity}</div>
                        <div className="flex gap-2">
                          <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--cos-leaf)]/20 text-[#4a9e6f] text-xs font-medium">
                            <Check size={12} /> Confirmar
                          </button>
                          <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--cos-fill)] border border-[var(--cos-hairline)] text-[var(--cos-stone)] text-xs font-medium">
                            <X size={12} /> Rechazar
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div
                        className={`max-w-[80%] px-3.5 py-2.5 rounded-2xl text-sm ${
                          msg.from === "user"
                            ? "bg-[var(--cos-ink)] text-[var(--cos-on-ink)] rounded-br-md"
                            : "bg-[var(--cos-fill)] text-[var(--cos-ink)] rounded-bl-md"
                        }`}
                      >
                        {msg.text}
                      </div>
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>

              {/* Typing */}
              {showTyping && msgIdx < messages.length && messages[msgIdx]?.from === "agent" && (
                <motion.div
                  className="flex items-center gap-2"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  <div className="bg-[var(--cos-fill)] rounded-2xl rounded-bl-md px-3.5 py-2.5">
                    <div className="flex gap-1">
                      {[0, 1, 2].map((i) => (
                        <motion.div
                          key={i}
                          className="w-1.5 h-1.5 rounded-full bg-[var(--cos-stone)]"
                          animate={{ y: [0, -4, 0] }}
                          transition={{ repeat: Infinity, duration: 0.6, delay: i * 0.15 }}
                        />
                      ))}
                    </div>
                  </div>
                </motion.div>
              )}
            </div>

            {/* Input */}
            <div className="px-4 py-3 border-t border-[var(--cos-hairline)] flex items-center gap-2">
              <div className="flex-1 h-9 rounded-lg bg-[var(--cos-fill)] border border-[var(--cos-hairline)] flex items-center px-3">
                <span className="text-xs text-[var(--cos-faint)]">Escribe a tu agente...</span>
              </div>
              <div className="w-8 h-8 rounded-lg bg-[var(--cos-ink)] text-[var(--cos-on-ink)] flex items-center justify-center">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 2L11 13" />
                  <path d="M22 2l-7 20-4-9-9-4 20-7z" />
                </svg>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
