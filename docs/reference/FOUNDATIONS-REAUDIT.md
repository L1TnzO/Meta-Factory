<!-- meta:doc sha=448ce868a11c72ec27ff7c452a4c81c12572db41 updated=2026-07-04T20:10Z -->
# FOUNDATIONS-REAUDIT — los fundamentos vs. la conducta medida

> tipo: reference (estable) · creado: 2026-07-04T02:58Z
> Re-auditoría S1 pedida por el ingeniero (2026-07-03): «si esto es bueno, ¿por qué no es el estándar
> de facto de Claude Code?» + veredicto por fundamento tras ~3 semanas de conducta MEDIDA (los
> fundamentos son del 2026-06-13/15 — git es la autoridad, no la sensación de meses). Autocontenido.
> Fundamentos auditados: `VISION.md` · `PRIMITIVES.md` · ADR-003/004/011/012/014 · `CONTEXT-ECONOMY.md`.

## 1. La pregunta incómoda, en cuatro partes

1. **Convergencia externa (validación).** PRIMITIVES §5 ya citaba (junio) que Spec Kit/Kiro/Tessl
   formalizan `spec→plan→tareas→verificación`; el SDD es dirección mainstream. Claude Code shippeó
   `opusplan` (Opus planifica · Sonnet ejecuta) — **ADR-021 es evolución convergente con el vendor**,
   alcanzada por medición propia. La diferencia que queda: ellos enforcean con prompts; acá con dientes
   (M0 rehúsa specs incompletas; RTM corta CI). Esa diferencia ES la tesis.
2. **Segmentación de régimen (por qué NO es el default).** El estándar optimiza el uso mediano
   interactivo, donde la revisión humana ES el gate y el costo fijo debe ser ~0. Este sistema optimiza
   **$/feature-VERIFICADA sin humano leyendo el código** — y la medición (DELEG-PAYOFF) mostró que ese
   régimen exige la columna ENTERA antes de pagar (gates rápidos + verificación hermética + slots
   cortos). Costo fijo alto, marginal bajísimo → nunca será default de mercado; es el diseño correcto
   para sistemas long-lived regenerables. Inversión honesta: para apps one-shot, vibe-coding + revisión
   humana es MÁS barato; ahí no competimos.
3. **Erosión por plataforma (el riesgo real).** La plataforma se come capas construidas acá (memoria,
   subagents, routing). Respuesta ya practicada: **podar cuando la plataforma absorbe** (ADR-019: índice
   semántico descartado por medición; MCP/vectorDB rechazado). Lo NO comoditizado — el moat: pin de
   re-derivación en clon limpio · RTM-desde-artefactos · contabilidad $/incremento (`meta outcome`).
4. **La evidencia más fuerte de sanidad: el sistema se poda a sí mismo.** Índice semántico descartado ·
   MCP rechazado · INC-5/6 N/A-por-medición · Snipe-IT degradado a techo de regresión · ADR-021 revisó
   el supuesto implícito «Opus siempre orquesta». El contrafáctico de un fundamento podrido existe y fue
   auditado: Professor Web Factory (gates que pasan por construcción, generación teatral) — lo opuesto
   medible de esto.

## 2. Veredicto por fundamento

| Fundamento | Veredicto | Evidencia dura |
| --- | --- | --- |
| SAFE-1..8 (prueba-por-bloqueo, re-derivación, slots acotados, sombra determinista, honestidad) | **SOSTENIDO** | 5 fábricas re-derivan `== pin`; falso-verde imposible por construcción; los N/A-por-medición SON SAFE-7 operando |
| Punto fijo (VISION §3) + ADR-006 (ASF como producto) | **COBRADO, con matiz** | F1 (2026-06-16, `F1-AUDIT-REGEN-VS-LEGACY.md`): la regenerada gana en GOBIERNO y prueba-por-unidad; la legacy gana en AMPLITUD hoy. El gap restante es CONTENIDO (backlog incremental), no fundación |
| ADR-011 (100% generado) + ADR-012 (primitivas-no-herramientas) | **SOSTENIDO, portante** | helpdesk first-try con 0 incrementos nuevos; línea día-a-día 0-modelo (palanca #1 del runbook ADR-021) |
| ADR-004 / CONTEXT-ECONOMY (bus de veredictos, ley de colocación) | **Necesario pero INSUFICIENTE → completado** | evitó dumps, pero la RESIDENCIA domina el costo (89% Opus delegando 159k tok) → ADR-021 (ruteo por sesión) lo completa por medición, no lo refuta |
| VISION §4 «Opus rara vez deriva a Sonnet» | **Cerrado por OTRO mecanismo** | tardó ADR-020+021; el mecanismo real (sesiones S1/S2/S3) ≠ el imaginado (derivación intra-sesión) — la física del cache decidió |
| Generalidad (ADR-012/014, espina SDD ADR-003) | **Sostenido con RECORTE medido** | Snipe-IT costó 17 ADOPTs → re-aim al sweet-spot 5-entidades (`benchmarks/sweet-spot-crud.yml`); el fundamento sobrevivió achicando su claim |
| VISION §5.2 (residuo semántico irreducible; el ingeniero no se sustituye) | **SOSTENIDO** | los gates no atrapan lógica bien-tipada-pero-equivocada ni no-ops semánticos; es lo que impide que «automatización total» sea fraude |

**Síntesis:** ningún fundamento resultó podrido; dos resultaron incompletos y se **completaron por
medición** (economía de contexto → ADR-021 · generalidad → sweet-spot). La opción honesta «botar y
simplificar» se ejecutó PARCIALMENTE varias veces — la única forma creíble de esa humildad.

## 3. La apuesta del ingeniero (humano en el spec; construcción máximamente automatizada)

No es dirección nueva: ES VISION §4 + ADR-011, y ya es VERDAD en el régimen cubierto (línea de producto
0-modelo; helpdesk first-try). El residuo real, y dónde se empuja:
- **Extender fábricas** (ejes nuevos) = juicio S1 — COST-DOWN lo abarata (S2 Sonnet ejecuta lo
  diseñado), no lo elimina.
- **Corrección semántica** (§5.2) no se elimina — **se muda al SPEC**: vocabulario más expresivo +
  eval-gates (DES-7) hacen que el RTM cubra más semántica → el residuo se achica asintóticamente,
  nunca a 0 (quien reclama 0 hace teatro).

## 4. Qué queda (cola ordenada al 2026-07-04, handoff de esta S1)

1. **Corrida S2 real** (Sonnet orquestador, `claude --model sonnet --agent orchestrator`) sobre un
   incremento con código → último KPI COST-DOWN §5 (opus-share ≤35%; hoy 3/4 KPIs verdes). La corre el
   ingeniero; S3 la lee con `meta outcome`.
2. **`SESSION-CLASS-AS-DATA`** — diseño DIFERIDO en `work/SESSION-CLASS-AS-DATA-INCREMENT.md`: clase de
   sesión como dato + `meta session` + diente de mismatch en SessionStart + cierre prescriptivo literal +
   schema-tooth del work-doc + 2 observers de medición (apertura fría-vs-caliente · pre-diseñado-vs-ad-hoc).
3. **Mediano plazo (el norte que F1 dejó):** cerrar el gap de CONTENIDO de la ASF regenerada vs la
   legacy con incrementos S2 baratos — la prueba definitiva de «regenerar > mantener», ahora viable
   por la economía ADR-021.
