---
sector: ai_ml
slug: ai_ml/llm_apps
title: "Aplicaciones LLM: prompts, tools, structured outputs, eval"
subtitle: "Cómo se construye una app sobre LLMs sin sustos"
tags: [llm, prompt, tool-use, function-calling, structured-output, eval, anthropic, openai]
weight: high
audience_levels: [mid, senior, staff]
when_to_ask:
  - "el usuario menciona LLM, GPT, Claude, Gemini, system prompt, tool use"
  - "habla de agents, function calling, structured outputs"
  - "describe evaluación o latencia de LLMs"
---

## Criterios clave

- **System prompt como contrato**: instrucciones claras, reglas numeradas, ejemplos. Versionar como código (git, tests).
- **Structured outputs siempre que se pueda**: JSON Schema (Anthropic tools, OpenAI structured outputs). NO parsear texto libre con regex.
- **Tool use con HITL** donde aplica: el modelo propone, el humano confirma operaciones destructivas. Como hacemos con `propose_*` en Universo Profesional.
- **Eval offline antes que online**: dataset golden de 30-100 casos. Cuando cambies prompt o modelo, corre eval; compare scores.
- **Eval online**: thumbs up/down, conversaciones tagged en producción, periodic review humana.
- **Latencia y coste**: cada turno mide tokens in/out y latencia. Prompt caching (Anthropic) reduce 70%+ de tokens repetidos.
- **Manejo de errores**: el LLM puede devolver basura, fallar tool calls, alucinaciones. Validar siempre la salida; reintentar con instrucciones más explícitas o degradar.
- **Privacy & PII**: scrub en logs, filtros en input/output según contexto, never train on user data por defecto.

## Preguntas guía

- "¿Cómo versionás tus prompts? ¿Tests de regresión?"
- "¿Usas structured outputs / function calling o parseo texto?"
- "¿Tienes dataset de eval offline? ¿Cuántos casos?"
- "Cuéntame del último prompt que cambiaste — ¿cómo evaluaste el impacto?"
- "¿Cómo gestionas la latencia (p99) y el coste por turno?"
- "¿Has tenido un incident con un LLM en prod? Alucinación, output mal formado, costes…?"

## Señales de seniority

- **Mid**: usa la API de OpenAI/Anthropic, prompts en strings inline, function calling básico.
- **Senior**: structured outputs sistemáticos, eval offline con dataset, prompt versioning, métricas de coste/latencia, tool use con HITL, conoce trade-offs Claude vs GPT vs open source.
- **Staff/Principal**: gobierna la AI strategy del producto, multi-provider con fallback, A/B testing de prompts, RAG cuando aplica, fine-tuning si vale el coste, privacy posture explícita (DPIA, contracts).

## Anti-patterns

- Prompt hardcoded como string de 2000 caracteres sin versionar.
- Parsear output con regex — un día el modelo cambia de mood y rompe el regex.
- Sin eval offline → cada prompt change es un experimento en producción.
- "El modelo aprenderá del feedback" — la API no, salvo fine-tuning explícito.
- Loop infinito de tool calls porque el modelo se enreda. Cap max iterations.
- PII en logs sin scrubber.
- Sin retry/backoff en API calls → rate limit y la app se rompe.

## Recursos

- Anthropic prompt engineering docs (excelentes, prácticas).
- OpenAI function calling + structured outputs docs.
- *Building LLM Powered Applications* (varios libros buenos, e.g. Valentina Alto).
- LangSmith / LangFuse para tracing + eval.
- Eugene Yan blog (eval, RAG, applied ML).
- Simon Willison blog (LLM práctica diaria).
- Anthropic's "Prompt Caching" docs (~70% input cost reduction).
