---
sector: ai_ml
slug: ai_ml/rag_pipelines
title: "RAG pipelines: chunking, retrieval, reranking, eval"
subtitle: "Lo que distingue un RAG que funciona de uno que solo demo-funciona"
tags: [rag, embeddings, retrieval, reranking, chunking, vector-db, hybrid-search]
weight: high
audience_levels: [mid, senior, staff]
when_to_ask:
  - "el usuario menciona RAG, retrieval, embeddings, vector DB"
  - "habla de Pinecone, pgvector, Weaviate, Qdrant"
  - "describe chunking, reranking, hybrid search"
---

## Criterios clave

- **Chunking estratégico**: por heading > por párrafo > por tokens. Overlap pequeño (10-15%) para preservar contexto en boundaries. NO uno-size-fits-all.
- **Embedding model match**: dimension acorde a vector DB, lenguaje del corpus, dominio. Text-embedding-3-small es default razonable; voyage-3, mistral-embed, cohere v3 también buenos. Para dominio médico/legal, embedders especializados pueden ganar.
- **Hybrid search** (vector + BM25/keyword) > vector-only para queries con términos específicos. RRF (Reciprocal Rank Fusion) para combinar.
- **Reranking** con cross-encoder (Cohere Rerank, BGE, Jina) cuando precision > recall. Top-50 retrieval → top-5 rerank.
- **Metadata filters** ANTES de la similitud (sector, fecha, source) — reducen el espacio de búsqueda y la latencia.
- **Eval con RAGAS** o similar: faithfulness (¿la respuesta se apoya en el contexto recuperado?), answer relevance, context precision/recall. Dataset humano de 50-100 Q&A.
- **Citations en la respuesta**: el LLM debe citar qué chunk vino de dónde. Permite debugging y user trust.
- **Refresh strategy**: cuando los docs cambian, re-embed solo lo afectado (content hash). No full rebuild.

## Preguntas guía

- "¿Cómo decidiste el tamaño y la estrategia de chunking?"
- "¿Vector-only o hybrid search? ¿Por qué?"
- "¿Usas reranking? ¿Cuándo aporta?"
- "¿Cómo evaluáis la calidad del RAG — eval offline, A/B?"
- "¿La respuesta cita las fuentes? ¿Cómo se renderizan en UI?"
- "¿Cómo actualizas el corpus cuando un doc cambia?"

## Señales de seniority

- **Mid**: pgvector / Pinecone wired, embedder OpenAI, top-k retrieval simple.
- **Senior**: chunking pensado, hybrid search, reranking cuando aplica, eval offline con RAGAS, metadata filters, citations en respuesta.
- **Staff/Principal**: diseña RAG multi-tenant, instrumenta eval continua, A/B testing de chunking/embedder/reranker, cost monitoring, optimiza p99 de retrieval (HNSW tuning, índices warm).

## Anti-patterns

- Chunkear todo a 512 tokens fijos sin importar el tipo de doc.
- Solo vector search en queries con nombres propios o IDs → BM25 lo haría mejor.
- Sin reranking, devolver top-20 chunks crudos al LLM → context bloat + alucinaciones.
- No tener ground truth → "el RAG funciona" sin evidencia.
- Re-embedar todo el corpus cada deploy → coste innecesario.
- Embedding model y dimension mezclados entre docs (1536-dim + 768-dim en mismo índice).
- Sin metadata: no se puede scoping por sector/tenant/fecha.

## Recursos

- *RAGAS* paper + library (eval metrics).
- Anthropic's "Contextual Retrieval" article (chunking con contexto adicional).
- Pinecone learning center (hybrid search, reranking explainers).
- *Embeddings: What they are and why they matter* — Simon Willison.
- LlamaIndex docs (muchos patrones implementados).
- Vespa.ai blog (búsqueda híbrida en profundidad).
- Eugene Yan: "Patterns for Building LLM-based Systems & Products".
