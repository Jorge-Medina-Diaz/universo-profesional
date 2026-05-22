---
sector: cloud
slug: cloud/aws_services
title: "AWS — servicios core + well-architected"
subtitle: "Cómo distingue un buen perfil AWS de uno que solo usó EC2 alguna vez"
tags: [aws, ec2, lambda, s3, rds, ecs, eks, iam, well-architected, cost]
weight: high
audience_levels: [mid, senior, staff]
when_to_ask:
  - "el usuario menciona AWS, Lambda, EC2, S3, RDS, Fargate, ECS, EKS, IAM"
  - "habla de Well-Architected Framework, cost optimization, multi-account"
  - "describe migraciones cloud o arquitecturas serverless"
---

## Criterios clave

- **Identity-first**: IAM con principle of least privilege. NO usar root account. AssumeRole entre cuentas. SCP en AWS Organizations. IAM Access Analyzer activo. Federación con SSO (no keys eternas).
- **Networking limpio**: VPC con subredes públicas/privadas separadas. NAT Gateway cuando hace falta. VPC endpoints (S3, DynamoDB) para evitar tráfico por internet. Security groups específicos por servicio, no `0.0.0.0/0` salvo bastions explícitos.
- **Compute correcto al caso**: Lambda para event-driven < 15min y picos impredecibles. ECS/Fargate para microservicios sin gestión de nodos. EKS para workloads serias con K8s expertise. EC2 con Auto Scaling Groups para legacy o costes optimizados con Spot/Reserved.
- **Datos**: RDS Multi-AZ para producción, read replicas para reads. Aurora si volumen alto. DynamoDB para key-value con escalado masivo + on-demand vs provisioned correcto. S3 con lifecycle policies + Intelligent-Tiering para coste.
- **Observabilidad**: CloudWatch logs estructurados + Metrics + Alarms. X-Ray traces. CloudTrail para audit. Costs en Cost Explorer + Budgets + Anomaly Detection. Tagging mandatory (Owner, CostCenter, Env).
- **Resiliencia**: Multi-AZ por defecto, multi-region para Tier-0. Backups automáticos con retention testada. Disaster Recovery con RTO/RPO documentados.
- **Coste consciente**: Reserved Instances / Savings Plans para baseline. Spot para batch. Right-sizing trimestral. Cost allocation tags. FinOps básico.

## Preguntas guía

- "¿Cómo manejas IAM — usuarios, roles, federación? ¿Has tenido un incident con credenciales?"
- "¿Por qué Lambda vs ECS/Fargate en tu caso?"
- "¿Multi-AZ o multi-region? ¿Has hecho failover real, no solo el botón?"
- "¿Cómo monitorizas costes? ¿Qué % del bill puedes asignar por team/feature?"
- "Cuéntame del último Well-Architected review que hiciste."
- "¿Tienes Infrastructure as Code para AWS? ¿Qué herramienta y por qué?"

## Señales de seniority

- **Junior**: usa la consola, conoce 3-5 servicios (EC2, S3, RDS, Lambda), credenciales en `~/.aws/credentials`. Buena para PoCs.
- **Mid**: maneja IAM roles, VPCs básicas, CloudWatch alarms, Terraform/CDK. Despliega prod sin asustarse. Tiene CloudTrail activo.
- **Senior**: arquitecturas multi-cuenta con Organizations + SCP, FinOps consciente, Well-Architected mental model implícito, monitorización proactiva, disaster recovery probado.
- **Staff/Principal**: gobierna la AWS strategy de varios equipos, define landing zones, cost allocation gobernance, security posture (GuardDuty + Security Hub + Config), enterprise agreements y negotiación.

## Anti-patterns

- IAM users con access keys eternas en lugar de SSO / AssumeRole.
- `0.0.0.0/0` en security groups de bases de datos "porque era más rápido".
- Lambda con timeouts altos haciendo workloads que deberían ser ECS.
- S3 buckets públicos por accidente (siempre `Block Public Access`).
- Sin tagging → no se puede atribuir coste, no se puede auditar.
- "Lo desplegamos a mano y nadie se acuerda de cómo" (no IaC).
- Monitorización solo de CPU, no de business metrics.

## Recursos

- AWS Well-Architected Framework (6 pilares: operational excellence, security, reliability, performance, cost, sustainability).
- "Cloud Native Patterns" — Cornelia Davis.
- AWS Re:Invent talks de architecture (búsquedas anuales).
- a16z FinOps Foundation Practitioner docs.
- AWS Cost Optimization Hub.
