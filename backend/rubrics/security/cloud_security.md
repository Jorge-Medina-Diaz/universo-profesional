---
sector: security
slug: security/cloud_security
title: "Cloud security: IAM, network, secrets, audit"
subtitle: "La nube no es segura por defecto: hay que configurarla"
tags: [iam, least-privilege, kms, vpc, audit, cloudtrail, security-groups]
weight: high
audience_levels: [mid, senior, staff]
when_to_ask:
  - "el usuario menciona IAM, roles, policies, KMS"
  - "habla de VPC, security groups, network segmentation"
  - "describe audit logs, CloudTrail, compliance"
---

## Criterios clave

- **IAM least privilege**: nadie con `Administrator` salvo break-glass. Roles por workload con scope mínimo. Service accounts en lugar de keys long-lived.
- **MFA obligatorio** para todos los humanos. Hardware keys (YubiKey) para roles privilegiados. SSO + SCIM para gestión centralizada.
- **Secrets management**: AWS Secrets Manager / GCP Secret Manager / Vault. Nunca env vars con secrets committed.
- **KMS para encryption at rest**: S3 buckets cifrados con KMS, DB cifradas, EBS volumes cifrados. Llaves rotadas según política (anual mínimo).
- **Network segmentation**: VPC con subnets públicas/privadas. NAT gateway para egress. Security groups restrictivos (deny-all + allow específico).
- **Audit logs always-on**: CloudTrail (AWS), Audit Logs (GCP), Activity Log (Azure). Inmutables (S3 con object lock). Retention >= 1 año.
- **Defender layers**: WAF (Cloudflare, AWS WAF) + DDoS protection + IDS/IPS según madurez.
- **Compliance posture**: SOC 2 / ISO 27001 / GDPR / HIPAA si aplica. Continuous compliance scanning (Drata, Vanta, Secureframe).

## Preguntas guía

- "¿Política de IAM — cómo se aprueban permisos privilegiados?"
- "¿MFA obligatorio? ¿Para todos o solo admins?"
- "¿Dónde viven los secrets de producción?"
- "Cuéntame de la network architecture — VPCs, subnets, NAT."
- "¿CloudTrail (o equivalent) always-on? ¿Retention?"
- "¿Compliance — qué standards aplican, cómo los mantienes?"

## Señales de seniority

- **Mid**: IAM roles básicos, MFA propio, conoce VPC + SG, secrets en parameter store.
- **Senior**: least privilege disciplinado, KMS bien usado, audit logs centralizados, network segmentation por workload, WAF configurado.
- **Staff/Principal**: governance de cloud accounts (Organizations, Control Tower), SCPs (service control policies), policy-as-code (OPA, Cedar), compliance program lead, incident response cloud-aware (token revoke, key rotation).

## Anti-patterns

- `Action: *` en IAM policies "por simplicidad".
- Long-lived access keys en lugar de roles asumidos.
- S3 buckets `public-read` sin necesidad.
- Security groups `0.0.0.0/0` en puertos no-80/443.
- Secrets en CI variables como plain text.
- CloudTrail sólo en una región (no multi-region trail).
- "Compliance es responsabilidad del CISO" — es de todos.
- Backups sin cifrado o en mismo account que prod (no cross-account).

## Recursos

- AWS Well-Architected Security Pillar.
- *AWS Security* (cantrill.io) — curso muy práctico.
- Cloud Security Alliance (CSA) Cloud Controls Matrix.
- CIS Benchmarks (AWS, GCP, Azure, K8s).
- *Securing the Cloud* — Vic Winkler.
- Marco Lancini / Cloud Security Wiki.
- HashiCorp Vault docs (secrets mgmt).
