---
sector: data_eng
slug: data_eng/streaming
title: "Streaming: Kafka, processing, exactly-once"
subtitle: "Cuándo streaming vale la pena y cómo no hacerlo mal"
tags: [kafka, pulsar, kinesis, flink, exactly-once, cdc, event-driven]
weight: medium
audience_levels: [mid, senior, staff]
when_to_ask:
  - "el usuario menciona Kafka, Pulsar, Kinesis, streaming"
  - "habla de event-driven, CDC, real-time"
  - "describe procesamiento streaming (Flink, Spark Streaming, ksqlDB)"
---

## Criterios clave

- **Streaming solo si la latencia importa** (< 1 min). Si tolera batch horario, batch gana siempre en simplicidad.
- **Particionado por key correcto**: order guarantees son por partición. Si tu key tiene skew (1 usuario = 80% tráfico), una partición se ahoga.
- **At-least-once + idempotencia downstream** > intentar exactly-once a nivel infra. Kafka Streams / Flink lo soportan, pero idempotencia downstream es más simple y robusta.
- **Schema registry obligatorio** (Confluent, AWS Glue, Apicurio). Producer no puede romper consumers silenciosamente. Compatibilidad backwards / forwards explícita.
- **CDC** (Debezium, AWS DMS) para syncar DB → warehouse en tiempo casi-real. Mucho más limpio que polling.
- **Backpressure y monitoring**: lag de consumers como métrica clave. Si lag crece, alerta y escala (más consumers, más particiones).
- **DLQ (Dead Letter Queue)** para mensajes que no se pueden procesar. Nunca descartar silenciosamente. Inspeccionar + replay.
- **Replay capability**: poder re-consumir desde un offset histórico. Retention de Kafka acorde al RTO.

## Preguntas guía

- "¿Por qué streaming y no batch?"
- "¿Cómo decides el partition key? ¿Has tenido skew?"
- "¿Aim for exactly-once o at-least-once + idempotencia?"
- "¿Schema registry? ¿Cómo gestionas compatibility?"
- "Cuéntame de un incidente de streaming — lag, mensajes mal formados, replay…"
- "¿DLQ y proceso de reprocesamiento?"

## Señales de seniority

- **Mid**: Kafka producer/consumer básico, conoce particiones, ha tocado Kafka Streams o Spark Streaming.
- **Senior**: schema registry usado, DLQ + replay, lag monitoring, particionado consciente, CDC bien entendido.
- **Staff/Principal**: define cuándo streaming sí vs no (no por moda), gobierna el platform (Kafka ops, retention policies, tier de tópicos), trabaja con ML team en feature stores en streaming.

## Anti-patterns

- Streaming porque mola, sin SLA real de latencia → complejidad sin valor.
- Sin schema registry → producer cambia, consumers rotos.
- Sin DLQ → mensajes rotos pierden silenciosamente o atascan la partición.
- Partition key con skew (`country=US`, `user_id` con power user dominante).
- Tu consumer hace I/O por mensaje → lag se acumula. Batchea.
- Exactly-once como goal absoluto cuando idempotencia downstream resuelve mejor.
- Sin observabilidad de lag → no sabes cuándo escalar.

## Recursos

- *Kafka: The Definitive Guide* — Shapira & Palino.
- *Streaming Systems* — Akidau, Chernyak, Lax (Google). Profundo.
- Confluent docs (Kafka mejor practices).
- Debezium docs (CDC).
- *Designing Data-Intensive Applications* — Kleppmann, capítulos 11 y 12.
- Flink + Kafka Streams docs (depending on stack).
