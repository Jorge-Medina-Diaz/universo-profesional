---
sector: ai_infra
slug: ai_infra/vector_databases
title: "Vector databases: Pinecone, Weaviate, pgvector, Milvus"
subtitle: "Cómo elegir y operar el almacén vectorial sin sobrepagar ni sufrir latencia"
tags: [vector-db, pinecone, weaviate, pgvector, milvus, qdrant, embedding, hnsw]
weight: medium
audience_levels: [mid, senior, staff]
when_to_ask:
  - "el usuario menciona Pinecone, Weaviate, Milvus, pgvector, Qdrant"
  - "habla de RAG, embeddings, ANN search, retrieval quality"
---

## Criterios clave

- **Elige según workload, no por hype**: pgvector si ya tienes Postgres y volumen razonable (<10M vectores), Pinecone para serverless managed, Weaviate cuando necesitas hybrid (vector+keyword) nativo, Qdrant para self-host con buen DX, Milvus para volumen masivo o multi-tenancy fuerte.
- **Index correcto**: HNSW por defecto (recall alto, latency baja). IVF si memoria limitada y aceptas recall menor. Flat solo en datasets <100k.
- **Hybrid search**: BM25 + vector + rerank (cross-encoder) en serie. Solo vector pierde recall en queries con términos raros / nombres propios.
- **Metadata filtering eficiente**: tags / namespaces / collections con índices secundarios. NO escanear todo el corpus y filtrar después.
- **Re-embedding lifecycle**: cuando cambias modelo de embedding, hay que re-embed todo. Plan migration con dual-write durante transición.
- **Evaluación de retrieval**: hit@k, MRR, nDCG vs ground truth manual. Tracear queries fallidas para mejorar chunking/embedding strategy.
- **Cost discipline**: vector dim importa (768 vs 1536 vs 3072). Reducir con MRL (Matryoshka) si el provider lo soporta.

## Preguntas guía

- "¿Por qué <vector db> y no <alternativa>? ¿Volumen real, latencia, budget?"
- "¿Tienes hybrid search o solo vector? ¿Cómo decidiste?"
- "¿Cómo mides retrieval quality — hit@k, MRR, eval humano?"
- "Cuéntame del último cambio de modelo de embedding — cómo migraste."
- "¿Qué dim de vector usas y por qué?"

## Señales de seniority

- **Mid**: usa pgvector básico o Pinecone con un SDK, sin métricas de quality.
- **Senior**: hybrid search funcionando, eval con hit@k, índice HNSW tuneado (M, efConstruction), migration de embeddings planificada.
- **Staff/Principal**: gobernance del retrieval (eval continuo, dataset golden), decisión de build vs buy con costes reales, multi-tenancy seguro con namespaces.

## Anti-patterns

- "Pinecone porque es lo que conocía" → coste 10x vs pgvector para volumen pequeño.
- Solo vector sin BM25 → recall pobre en queries con keywords específicas.
- Sin re-rank → top-1 es ruido cuando los embeddings son ambiguos.
- Migrar modelo sin dual-write → downtime mientras re-embeas todo.
- Métricas vanity ("p99 < 50ms") sin evaluar quality.
- Sin trace de queries fallidas → no aprendes dónde mejorar.

## Recursos

- "Building LLM Applications" (Chip Huyen, capítulo RAG).
- Pinecone learning center + Weaviate / Qdrant docs.
- pgvector docs + benchmarks recientes.
- RAGAS / TruLens para eval de RAG.
- Greg Kamradt's blog (chunking + retrieval evals).
