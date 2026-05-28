# Pendientes — Universo Profesional

> Última actualización: 2026-05-26  
> Estado post-Swarm A + C (demo-ready + MCP adoption).

---

## 🔴 Críticos — Bloquean producción real

| # | Tema | Qué falta | Riesgo |
|---|------|-----------|--------|
| 1 | **Storage S3** | Solo existe `FilesystemStorageAdapter`. Falta adaptador S3 con boto3 para avatares y documentos en producción. | Pérdida de datos en redeploys / volúmenes locales |
| 2 | **2FA/TOTP** | Campos `mfa_secret` y `mfa_enabled` existen en User pero no hay endpoints de enrolamiento ni verificación. | Cumplimiento de seguridad incompleto |
| 3 | **Mypy strict** | ~495 errores preexistentes en modo strict. No bloquea CI (`continue-on-error: true`) pero dificulta refactors. | Deuda técnica creciente |
| 4 | **Tests e2e/integración fragiles** | Fallos históricos por contención de DB y event loops en Windows. CI usa Ubuntu single-process. | Regresiones silenciosas |

---

## 🟡 Importantes — Mejoran producto o operaciones

| # | Tema | Qué falta | Impacto |
|---|------|-----------|---------|
| 5 | **SEO/GEO landing** | No hay `llms.txt`, Schema.org markup, meta tags optimizados, ni texto para AI search. | Tráfico orgánico = 0 |
| 6 | **Application tracker** | El PLAN.md menciona "applications tracker" en Premium. No existe módulo de seguimiento de candidaturas. | Feature gap vs. competidores |
| 7 | **Match scoring detallado** | `match_job_to_profile` existe pero sin score desglosado (skills, experiencia, cultura). | Valor percibido bajo |
| 8 | **Multi-idioma completo** | i18n está configurado pero faltan traducciones EN/CA/gl para muchas páginas. | Mercado limitado a ES |
| 9 | **Recordatorios** | El PLAN.md menciona recordatorios en Premium. No existe sistema de recordatorios. | Feature gap |
| 10 | **Alertas MCP por cuota** | Los usuarios Premium/Pro no reciben aviso cuando se acercan al límite de invocaciones MCP. | Bad UX, sorpresas de facturación |

---

## 🟢 Deseables — Nice to have

| # | Tema | Qué falta | Impacto |
|---|------|-----------|---------|
| 11 | **BYOK (Bring Your Own Key)** | Pro permite BYOK de LLM pero no hay UI para configurar claves propias. | Diferenciador Pro incompleto |
| 12 | **Export JSON Resume / Europass / MAC** | Solo PDF/DOCX. Falta exportación estructurada. | Interoperabilidad |
| 13 | **Dark mode polish** | Existe `data-theme="dark"` pero no está 100% consistente en todas las páginas. | Pulido visual |
| 14 | **Playwright E2E** | No hay tests E2E del golden path. | Regresiones en frontend |
| 15 | **Observabilidad avanzada** | Métricas de negocio (funnel de onboarding, CVs generados/mes, trial→paid conversion) en dashboard. | Toma de decisiones a ciegas |

---

## 🚀 Próximos pasos sugeridos (post-deploy)

1. **Smoke test del deploy**: `curl /readyz`, registro, onboarding, generar CV, mock checkout.
2. **Activar Stripe test**: `STRIPE_PROVIDER=real` + `sk_test_...` → probar checkout real con tarjeta de test.
3. **Activar Resend**: `EMAIL_PROVIDER=resend` + `RESEND_API_KEY` → probar emails de verificación.
4. **Activar Anthropic**: `ANTHROPIC_API_KEY` → probar generación de CV con LLM real.
5. **Application tracker** → siguiente feature de producto más valiosa.
