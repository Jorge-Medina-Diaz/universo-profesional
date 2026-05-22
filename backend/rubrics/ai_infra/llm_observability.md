---
sector: ai_infra
slug: ai_infra/llm_observability
title: "LLM observability: tracing, token tracking, latency SLOs, cost dashboards"
subtitle: "Sin esto, cada cambio de prompt es un experimento ciego en producción"
tags: [observability, llm, langsmith, langfuse, phoenix, traces, tokens, cost]
weight: high
audience_levels: [mid, senior, staff]
when_to_ask:
  - "el usuario menciona LangSmith, LangFuse, Phoenix, Helicone, traces LLM"
  - "habla de token tracking, cost per call, latency p99 de modelos"
---

## Criterios clave

- **Traces por turno**: cada call al LLM emite trace estructurado con (input, output, tool_calls, tokens_in, tokens_out, latency_ms, cost_usd, model, status, error_code, conversation_id). Sampling adaptativo (head + tail).
- **Token economics visibles**: dashboard con tokens/conversación, cost/user, cost/feature. Alerts en bursts anómalos.
- **Latency SLOs por workload**: chat conversacional <2s p95, batch async <30s p95, eval offline sin SLA. Burn-rate alerts.
- **Quality monitoring**: human feedback (thumbs up/down), implicit signals (re-prompt rate, abandoned conversations), periodic human eval samples.
- **Replay capacity**: cualquier trace debe poder reproducirse exactamente (mismo prompt, modelo, temperature, seed cuando aplica).
- **Multi-provider routing visible**: si routeas Claude vs GPT vs local, el dashboard muestra mix + fallback rate.
- **Prompt versioning**: cada prompt change = nueva versión en eval suite. Trace muestra qué versión de prompt corrió.

## Preguntas guía

- "¿Qué herramienta de tracing usas? ¿Por qué esa?"
- "¿Cuánto cuesta atender un usuario activo al mes? ¿Lo sabes con precisión?"
- "¿Tienes SLO de latency end-to-end? ¿Cómo alertas si lo violas?"
- "Cuéntame de un cambio de prompt que regresionaste con el trace."
- "¿Cómo capturas quality feedback en producción?"

## Señales de seniority

- **Mid**: usa logging básico (print/log de tokens), revisa coste mensual a ojo.
- **Senior**: LangSmith/LangFuse/Phoenix con traces estructurados, dashboards Grafana con cost+latency+quality, eval suite atada a CI.
- **Staff/Principal**: gobierna observabilidad LLM como parte del SLO general, alerts proactivos, cost forecast, multi-provider strategy con datos.

## Anti-patterns

- Solo console.log → cuando algo va mal en prod, sin replay no puedes diagnosticar.
- Cost tracked manualmente cada fin de mes → te enteras del problema 3 semanas tarde.
- Tracking solo de "happy path" → los edge cases (errores, retries) son donde el coste se dispara.
- Sin sampling → almacenas todos los traces y el bill de observability supera al LLM.
- Prompt sin versioning → "antes esto funcionaba" sin forma de bisectar.

## Recursos

- LangSmith docs (es la referencia más completa).
- LangFuse (open source alternative) + Phoenix (Arize) docs.
- Helicone para proxy-based tracking.
- OpenTelemetry semconv para GenAI (spec emergente, vale la pena seguirla).
- Anthropic + OpenAI usage APIs.
