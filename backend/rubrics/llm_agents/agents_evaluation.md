---
sector: llm_agents
slug: llm_agents/agents_evaluation
title: "Evaluación de agentes: task evals, cost/latency, HITL, observability"
subtitle: "Cómo demostrar que tu sistema agéntico realmente funciona"
tags: [eval, observability, langsmith, langfuse, phoenix, regression, hitl, metrics]
weight: high
audience_levels: [mid, senior, staff]
when_to_ask:
  - "el usuario menciona eval, evaluación, success rate, instruction following"
  - "habla de LangSmith, LangFuse, Phoenix, traces, regression suites"
  - "describe cómo mide la calidad de un agente"
---

## Criterios clave

- **Eval con dataset golden por task**: 30-100 casos representativos. Cubre happy path, edge cases, adversarial. Mantenlo en git, no en una hoja.
- **Métricas por nivel**:
  - *task-level*: success rate (¿completó la tarea?), instruction following (¿cumplió constraints?), output quality (judge LLM o human-eval).
  - *agent-level*: cost per task (input+output tokens × precio), latency p50/p95/p99, hop count (cuántas iteraciones), tool call success rate.
  - *system-level*: % de tasks que requirieron HITL, drop-off por iteración.
- **Eval offline antes que online**: cuando cambies prompt, modelo, tool, ejecuta el dataset golden — compara scores y costs. Sin esto, cada cambio es un experimento en producción.
- **Eval online continua**: muestra de conversaciones reales semanal, tagging humano, regresión vs baseline. Métricas en dashboards (no en heads de devs).
- **HITL como signal, no como gap**: cada vez que un humano corrige al agente es un eval point negativo — captúralo para retrain el dataset golden.
- **Observability estructurada**: cada turno emite trace con (input, output, tools_called, tokens, cost, latency, status). LangSmith / LangFuse / Phoenix.
- **Eval-driven development**: TDD-style — escribe el caso golden ANTES del fix. Si el modelo nuevo pasa el golden, ship; si no, no.

## Preguntas guía

- "¿Tienes dataset de eval offline? ¿Cuántos casos, en qué formato?"
- "¿Qué métrica de success usas — exact match, judge LLM, human-eval?"
- "¿Cuál es el cost-per-task promedio? ¿Tienes presupuesto?"
- "Cuéntame del último cambio de prompt — ¿cómo evaluaste el impacto?"
- "¿Qué % de tasks requieren intervención humana? ¿Cómo lo trackeás?"
- "¿Hay tasks que el agente NUNCA debería ejecutar solo? ¿Cómo lo enforce?"
- "Cuando cambias de Claude 3.5 a Claude 4.7, ¿qué hace ese paso?"

## Señales de seniority

- **Mid**: eval ad-hoc (corro 3 casos, los miro), sin dataset versionado, métricas en logs sueltos. "Funciona en mi demo".
- **Senior**: dataset golden en git, métricas estructuradas (success_rate, cost, latency), trazas en LangSmith/Phoenix, regression antes de cada deploy. HITL rate medido.
- **Staff/Principal**: eval framework propio (custom judges, multi-dimensional), eval continuo en producción con shadow runs, A/B testing de prompts y modelos, eval-budget como % de cost del producto, governance (safety evals, bias evals).

## Anti-patterns

- "El usuario nos dice que funciona" — sin métrica, sin baseline, sin replay capacity.
- Cambiar prompt sin eval suite → un día el modelo deja de cumplir un constraint sutil y nadie se entera durante semanas.
- Métricas solo del happy path; los edge cases son donde te explota.
- Judge LLM mal calibrado: usas Sonnet para evaluar Haiku y sobreestima sistemáticamente. Calibra con human-eval.
- No medir cost en eval offline → en prod un cambio "barato" se vuelve cost-overrun.
- HITL rate alto sin alarma: el agente está fallando silenciosamente y los humanos lo están parchando.
- Sin replay de traces: cuando algo va mal, no puedes reproducir.

## Recursos

- "Evaluating LLM Applications" (LangChain blog, Eugene Yan).
- LangSmith eval framework + datasets.
- LangFuse traces + scoring.
- Phoenix (Arize) para tracing + eval LLM-as-judge.
- Anthropic eval cookbook: judge prompts canónicos.
- "AI Engineering" (Chip Huyen, 2024) — capítulo de eval es referencia.
- Benchmark agentic: SWE-bench, GAIA, AgentBench (referencia para calibrar tu propio dataset).
