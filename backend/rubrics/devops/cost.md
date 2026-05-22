---
sector: devops
slug: devops/cost
title: "FinOps: gestión de coste cloud"
subtitle: "Cómo se mide y se controla el gasto sin frenar el producto"
tags: [finops, cost, aws, gcp, reserved-instances, spot, rightsizing]
weight: medium
audience_levels: [mid, senior, staff]
when_to_ask:
  - "el usuario menciona FinOps, cost optimization, AWS bills"
  - "habla de reserved instances, spot, right-sizing"
  - "describe gestión de coste cloud o billing alerts"
---

## Criterios clave

- **Cost allocation primero**: tags en TODOS los recursos cloud (`team`, `service`, `env`, `cost_center`). Sin tags, el billing report es opaco.
- **Right-sizing iterativo**: empieza con t-shirt sizes razonables, observa métricas (CPU, mem, IOPS) durante 2-4 semanas, ajusta. Repetir cada Q.
- **Compute commitment**: workloads estables → reserved (1-3 años) o savings plans. Workloads variables → on-demand. Workloads tolerantes a interrupción (batch, training) → spot/preemptible (60-80% descuento).
- **Storage tiering**: hot (S3 Standard / SSD), warm (S3 IA / cold HDD), archive (Glacier / archive tier). Lifecycle policies automáticas.
- **Egress es el silent killer**: cross-region/cross-cloud egress cuesta mucho. CDN (CloudFront, Cloudflare) para hot content.
- **Budget alerts**: thresholds por team/service. Si supera 80% del budget mensual, alerta. 100% → discusión obligatoria.
- **FinOps maturity**: crawl (visibility) → walk (allocate + optimize) → run (automate + culture). No saltes etapas.

## Preguntas guía

- "¿Tenéis cost allocation tags? ¿Cuán completos?"
- "¿Cuándo decidisteis usar reserved/savings plans? ¿Y spot?"
- "¿Cómo monitorizáis cost en day-to-day? ¿Alertas, dashboards, reviews?"
- "Cuéntame de una optimización de coste real — ¿cuánto ahorraste?"
- "¿Quién owner del cost — DevOps, FinOps, Finance? ¿Cómo coordinan?"
- "¿Tenéis policies de auto-shutdown para envs de dev?"

## Señales de seniority

- **Mid**: conoce tipos de instancia y sus precios, ha pedido reservas alguna vez.
- **Senior**: usa cost-allocation tags, right-sizing trimestral, mezcla on-demand + reserved + spot conscientemente, alerta de budget, lifecycle de S3.
- **Staff/Principal**: estrategia FinOps multi-cloud, governance + showback/chargeback, KPIs de coste por servicio/usuario, predicción de coste para nuevas features, negociación con cloud vendors.

## Anti-patterns

- Instancias `xlarge` "por si acaso" sin medición.
- 100 NAT gateways en cuentas dev sin apagar.
- S3 Standard para data que no se accede en 6 meses.
- Cross-region replication "para HA" sin entender el coste de egress.
- No tener budget alerts hasta que llega la factura.
- "FinOps es responsabilidad del CFO" — no, es responsabilidad de ingeniería + finance juntos.

## Recursos

- *Cloud FinOps* — J.R. Storment & Mike Fuller (libro de referencia).
- FinOps Foundation (framework + certificaciones).
- AWS Cost Explorer + CUR (Cost & Usage Report) — el dato real.
- Cloudability / Vantage / Finout (tools FinOps específicas).
- AWS Well-Architected Framework — pillar de Cost Optimization.
- Corey Quinn (Duckbill) blog y newsletter (humor + sustancia AWS cost).
