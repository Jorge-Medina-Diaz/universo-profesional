---
sector: llm_agents
slug: llm_agents/agents_frameworks
title: "Frameworks de agentes: CrewAI, LangGraph, Autogen, Agno, LlamaIndex"
subtitle: "Cuándo y cómo elegir el framework adecuado para sistemas agénticos"
tags: [agents, agno, crewai, langgraph, autogen, llamaindex, multi-agent, orchestration]
weight: high
audience_levels: [mid, senior, staff]
when_to_ask:
  - "el usuario menciona CrewAI, LangGraph, Autogen, Agno o LlamaIndex Agents"
  - "habla de single-agent vs multi-agent, orchestrator-workers, hierarchical, swarm"
  - "describe un sistema con varios agentes coordinándose"
---

## Criterios clave

- **Match framework con problema, no al revés**: un single-agent con tool use cubre el 70% de casos. Multi-agent justifica complejidad sólo cuando hay roles realmente distintos (planner / executor / critic) o paralelismo necesario.
- **Abstracción vs control**: CrewAI y Autogen son altos en abstracción (rápidos para prototipo, dolorosos para debug); LangGraph y Agno expone más el grafo (más boilerplate, más visibilidad). Elige según lo crítico que sea el debugging.
- **Modelo de coordinación explícito**: orchestrator-workers (un agente decide qué hacer), hierarchical (manager → workers), swarm (peer-to-peer), pipeline (DAG). Documentar cuál usas y por qué.
- **State management**: agentes con estado (memoria, vector store) versus stateless. Cada turno debe ser reproducible en lo posible — guardar trazas, no sólo el output final.
- **Tool registry estable**: las herramientas son contratos. Versionar; tener naming consistente; rate-limit por tool si tocan APIs externas.
- **Fallbacks por agente**: model routing (Claude para razonamiento, GPT-4o-mini para extracción barata, local para clasificación). No casarse con un proveedor.
- **Human-in-the-loop bien diseñado**: operaciones destructivas (escribir DB, mandar email) deben pasar por confirmación. Patrón "external execution" / tool aprobado por usuario.

## Preguntas guía

- "¿Por qué elegiste <framework> en lugar de un solo agente con tool calling?"
- "¿Cuántos agentes tiene el sistema y qué rol distinto cumple cada uno?"
- "¿Cómo coordinas: hay un planner o cada agente decide? ¿Cómo evitas loops?"
- "¿Dónde se almacena el estado entre turnos — context, vector DB, base relacional?"
- "Cuéntame de un bug raro de multi-agent que tuviste que depurar — ¿cómo lo encontraste?"
- "¿Tienes HITL para acciones críticas? ¿Cómo decides qué es crítico?"

## Señales de seniority

- **Mid**: usa el framework siguiendo el quickstart, agentes con un único rol, sin métricas de calidad. Llama tools básicas (search, code interpreter).
- **Senior**: conoce trade-offs entre 2-3 frameworks, elige por motivos concretos, define agent contracts (input/output schema), versiona prompts, mide success rate por agent.
- **Staff/Principal**: gobierna la estrategia agéntica (qué problemas merecen agentes, cuáles no), mezcla frameworks cuando hace falta, define HITL policy a nivel producto, mantiene cost-per-task como SLO.

## Anti-patterns

- "Empiezo con multi-agent porque suena potente" — over-engineering. Empieza con 1 agente.
- Agent con 12 tools sin priorización: el modelo se atasca eligiendo. Máximo 5-7 tools por agent.
- Hardcodear el framework en la lógica de negocio. Aísla detrás de una interfaz para poder cambiar.
- Sin observability: no sabes qué tool falló, ni en qué turno, ni cuánto costó. Logging estructurado + tracing es no-negociable.
- Ignorar context-window: en multi-agent la conversación crece exponencial. Resúmenes, slicing, vector recall.
- "Lo orquestamos todo con prompts en JSON dentro del system" — frágil. Usa el grafo del framework.

## Recursos

- LangGraph docs: state graph patterns, debugging traces.
- CrewAI quickstart + papers de "Agentic AI" 2024-2025.
- Agno docs (team + member, tools, knowledge, RunContext).
- Autogen Studio para prototipos visuales.
- "Building Effective Agents" (Anthropic, 2024) — paper canónico sobre patterns.
- LangSmith / LangFuse / Phoenix para tracing agéntico.
