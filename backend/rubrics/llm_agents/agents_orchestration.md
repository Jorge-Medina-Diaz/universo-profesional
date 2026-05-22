---
sector: llm_agents
slug: llm_agents/agents_orchestration
title: "Orquestación de agentes: planning, memoria, A2A, MCP, fallbacks"
subtitle: "Cómo hacer que varios agentes (o uno solo con muchas tools) trabajen sin caos"
tags: [orchestration, planning, react, reflexion, memory, mcp, a2a, hitl, cost]
weight: high
audience_levels: [mid, senior, staff]
when_to_ask:
  - "el usuario menciona planning, ReAct, Reflexion, memory, A2A, MCP"
  - "describe agentes que se llaman entre sí o coordinan tareas largas"
  - "habla de cost management, fallbacks, model routing"
---

## Criterios clave

- **Planning explícito**: ReAct (think→act→observe) para tareas cortas, plan-and-execute (planner separado del ejecutor) para tareas largas, Reflexion (self-critique) cuando hay margen de mejora claro. No "todo es ReAct".
- **Memoria por capas**:
  - *short-term*: el context window — limpia agresivamente.
  - *episodic*: log de la sesión actual en estructura recuperable (no sólo texto plano).
  - *long-term semántica*: vectores con expiración y re-evaluación; no acumules basura.
  - *factual estructurada*: base de datos (notes, profile, etc.) — no la "metas en el embedding".
- **Tool composition**: tools deben ser idempotentes y devolver structured data. Compose en el código (no esperando que el LLM acierte la secuencia siempre).
- **Protocolos inter-agente**: MCP para tool-sharing entre runtimes, A2A (Google) o REST estable para agente-a-agente entre servicios. Versionar los contratos.
- **HITL gates**: cualquier operación destructiva o irreversible (write external API, mandar mensaje, gastar dinero) requiere confirmación humana o ID-de-aprobación explícito.
- **Cost management**: presupuesto por task (max_tokens, max_iterations, timeout). Model routing barato→caro (e.g. clasifica con Haiku, razona con Sonnet, escribe con Opus si vale).
- **Failure modes conocidos y manejados**: loops infinitos (cap iterations), hallucinated tool names (whitelist), output mal formado (retry con structured output, fallback a humano).

## Preguntas guía

- "¿Cómo decide el agente qué hacer next? ¿ReAct, plan-and-execute, otro?"
- "¿Qué memoria mantienes entre turnos y dónde vive?"
- "¿Tienes MCP o A2A para compartir tools entre runtimes? Si no, ¿por qué?"
- "¿Cuál es el budget por task y cómo lo enforzás?"
- "¿Has tenido un loop infinito o cost-overrun? Cuéntame cómo lo detectaste."
- "¿Qué acciones REQUIEREN aprobación humana?"
- "¿Cómo routeas entre modelos (Claude vs GPT vs local)? ¿Por qué?"

## Señales de seniority

- **Mid**: planning implícito en el system prompt, todo en el context window, sin protocolos inter-agente, sin budget. Funciona en demos.
- **Senior**: planning explícito (separated planner), memoria con capas, tool registry versionado, cost cap por session, HITL en operaciones críticas, model routing básico.
- **Staff/Principal**: políticas de orchestration a nivel producto, MCP servers internos, A2A entre microservicios agénticos, eval-driven optimization de cost/latency, governance del comportamiento agéntico (safety, audit log).

## Anti-patterns

- Contexto sin limpiar: el system + tools + history llegan al límite y el modelo empieza a olvidar instrucciones. Hay que resumir y descartar.
- Memoria long-term que crece sin garbage collection: la calidad del retrieval cae linealmente.
- "Multi-agent porque se ve cool" sin un planner que decida — caos.
- Tools no idempotentes (POST sin idempotency key) → reintentos crean basura.
- Operaciones destructivas sin HITL: un bug y borras producción.
- Sin observability inter-agente: cuando algo falla, "no sabemos por qué".
- Hardcodear el modelo: cuando sube de precio o sale uno mejor, tienes que reescribir todo.

## Recursos

- "Plan-and-Solve Prompting" (paper, 2023).
- "Reflexion: Language Agents with Verbal Reinforcement Learning" (paper).
- MCP spec (Model Context Protocol, Anthropic): tools, prompts, resources.
- Google A2A protocol (2024-2025) para agent-to-agent comms.
- "Constitutional AI" + safety patterns (Anthropic).
- LangSmith traces como herramienta de debugging agéntico.
- Notebooks de Cookbook de Anthropic (tool use, agents).
