---
sector: ai_ml
slug: ai_ml/eval_finetune
title: "Evaluación y fine-tuning de modelos"
subtitle: "Datasets, métricas, splits, y cuándo realmente fine-tunear"
tags: [eval, fine-tuning, lora, dataset, train-test-split, metrics, ml-ops]
weight: high
audience_levels: [mid, senior, staff]
when_to_ask:
  - "el usuario menciona fine-tuning, LoRA, training, evaluación"
  - "habla de datasets, train/val/test, métricas"
  - "describe MLOps, model deployment, eval offline+online"
---

## Criterios clave

- **Dataset primero, modelo después**: 80% del éxito está en el dataset. Calidad, diversidad, cobertura de edge cases.
- **Train/val/test split** con criterio (no random si hay temporalidad o usuarios — leak prevention). Test set se usa solo al final.
- **Métricas alineadas con el negocio**: accuracy es raramente la métrica útil. F1, precision/recall por clase, AUC, calibración. En LLM: faithfulness, helpfulness, harmlessness.
- **Baseline siempre primero**: regla simple, modelo pequeño, GPT-4 zero-shot. Tu modelo fine-tuned tiene que **batir** algo.
- **Fine-tune solo si**: prompt engineering + few-shot + RAG no alcanzan; tienes 100+ ejemplos de calidad; el coste de inferencia justifica un modelo más pequeño; necesitas latencia baja.
- **LoRA/QLoRA** antes que full fine-tune en LLMs. Más rápido, más barato, casi el mismo rendimiento para tareas estrechas.
- **Eval offline + online**: offline en test set (regression checks), online en producción con guardrails (canary 1% → 10% → 100%).
- **Versionado**: datasets versionados (DVC, LakeFS), checkpoints con metadata (training data hash, hyperparams), modelo registry (MLflow, W&B).

## Preguntas guía

- "¿Cómo es tu dataset — cómo lo curaste, cuántos ejemplos?"
- "¿Cómo divides train/val/test? ¿Has tenido leakage?"
- "¿Cuándo decides fine-tunear vs quedarte con prompt + few-shot?"
- "¿LoRA o full fine-tune? ¿Por qué?"
- "Cuéntame del último model release — ¿qué eval offline + online corriste?"
- "¿Cómo monitorizas drift en producción?"

## Señales de seniority

- **Mid**: fine-tune con script suelto, métrica única (accuracy), train/val/test random.
- **Senior**: pipeline reproducible (DVC + script o configs), baselines, split con criterio, LoRA, eval offline + smoke online, model versioning.
- **Staff/Principal**: gobierna la MLOps platform, instrumenta eval continua en prod, drift detection, A/B testing entre modelos, RLHF si aplica, governance (data, compliance, fairness).

## Anti-patterns

- Test set contaminado con train (leakage temporal o por user_id).
- Una sola métrica → "97% accuracy" en un dataset desbalanceado donde la mayoría es la clase trivial.
- Fine-tunear sin baseline → no sabes si vale la pena.
- Hyperparam tuning manual sin tracking → no reproducible.
- Modelo en prod sin métrica de calidad observada (silently degrading).
- "El experto del equipo lo eval visualmente" — no escala.
- Train + inference con código distinto → silently different transforms.

## Recursos

- *Designing Machine Learning Systems* — Chip Huyen.
- *Building Machine Learning Pipelines* — Hannes Hapke.
- Hugging Face PEFT docs (LoRA practical).
- W&B + MLflow docs.
- Eugene Yan: eval patterns + ml-design-docs.
- *Machine Learning Yearning* — Andrew Ng (gratis online, fundamentos).
- Anthropic / OpenAI fine-tuning guides (cuándo sí, cuándo no).
