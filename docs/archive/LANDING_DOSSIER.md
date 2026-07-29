# Dossier: Discurso e Imagen de Producto — Universo Profesional

> Version para rediseño de landing publica (sin auth). Objetivo: YC Demo Day caliber.

---

## 1. Narrativa Central

**Tu carrera no es un documento. Es un universo.**

Durante decadas hemos tratado nuestra trayectoria profesional como si fuera un archivo de Word: estatico, plano, incapaz de crecer. Cada vez que cambiamos de trabajo, pivotamos de sector o aprendemos algo nuevo, tenemos que reescribirlo desde cero. Es un sinsentido.

**Universo Profesional** es el primer Career OS que modela tu trayectoria como lo que realmente es: un **grafo de conocimiento vivo**, conectado, en evolucion. Un sistema donde cada experiencia, skill, proyecto y certificacion ocupa su lugar en un universo estructurado que crece contigo.

Y lo mejor: **no lo mantienes con formularios. Lo mantienes hablando.**

---

## 2. Lo que nos hace rompedores (moat)

### A. Modelo de datos: universo vs. documento
- Competencia (Zety, Kickresume, Rezi, Teal): multiples CVs estaticos. El modelo de datos ES el documento.
- Nosotros: un grafo de conocimiento personal con 11 tipos de entidades, cada una con embeddings semanticos, historial de cambios y evidencias cruzadas.
- Resultado: no editas un documento. Explotas un corpus.

### B. Coherence Engine: nada se acumula a ciegas
- Cada escritura pasa por un motor de coherencia que busca entidades existentes y aplica reglas declarativas de fusion.
- Si mencionas "Python" hoy y "5 anos de Python" dentro de 6 meses, el sistema fusiona, no duplica.
- Esto no existe en ningun competidor.

### C. 28 especialistas de IA coordinados
- No es un chatbot con CRUD. Es un coordinador + 28 especialistas.
- Cada especialista entiende su dominio y propone cambios via HITL cards.
- El usuario confirma con un toque. Nada se escribe sin permiso.

### D. Servidor MCP remoto (OAuth 2.1 + PKCE)
- El unico Career OS espanol que expone un servidor MCP nativo.
- Desde Claude Code, Cursor, Codex: actualiza tu perfil y genera CVs en lenguaje natural.

### E. Grafo de conocimiento + ontologia ESCO
- Apache AGE + pgvector: cada entidad es un nodo, cada relacion una arista tipada.
- Anclado a ESCO (ontologia oficial de la UE): ~3k ocupaciones, ~14k skills.

### F. RAG hibrido de 3 carriles
- BM25 + dense cosine + PPR (Personalized PageRank) + RRF k=60.
- El CV se construye SOBRE tu corpus real, no alucinado.

### G. Memoria agentica de 4 capas
1. Entidades estructuradas (SQL)
2. Grafo AGE (Cypher)
3. Notas (markdown + tags)
4. Memoria semantica/procedural (self-learning)

### H. RGPD nativo, hosting UE
- Datos en Europa, encriptacion at-rest, derecho al olvido.

---

## 3. Tone of Voice

**Calido pero ambicioso. Tecnico pero humano. Europeo pero global.**

---

## 4. Estructura de la landing

```
1. Hero (100vh) — fondo de particulas/nodos + headline + subhead + CTAs
2. Trust bar — logos de integraciones compatibles
3. El problema — contraste visual: Word plano vs. universo vivo
4. Feature grid (6 pilares) — con iconos y micro-demos
5. El flujo — 4 pasos numerados, horizontal
6. MCP section — codigo + visual de integracion
7. Graph teaser — preview del grafo visual
8. Pricing / Trial — 7 dias gratis, sin tarjeta
9. FAQ (acordeon) — 5-6 preguntas clave
10. Footer — links legales + CTA final
```

## 5. Visual Language

### Concepto: "Orden vivo"
- No es caos. Es estructura organica.
- Un grafo de nodos conectados que respira, se expande, se contrae.
- Colores calidos sobre fondo claro (el sistema Pirsch es nuestro ADN).
- Sunbeam (#ffda6e) = energia, accion, el sol.
- Leaf (#6ece9d) = crecimiento, vida, evolucion.
- Nova (#00d4aa) = inteligencia, agentes, el futuro.
- Ink (#000000) = estructura, verdad, contorno.
