<!-- meta:doc sha=5072cdeb898954a0d62531a6c90c122436e7ba62 updated=2026-07-08T02:05Z -->
# ADR-023 — Generación model-nativa + piezas de comunidad: la fábrica es la spec y el perfil de verificación; el codegen de templates se congela

| Campo | Valor |
| --- | --- |
| Estado | Aprobado |
| Fecha | 2026-07-08T02:04Z |
| Decide | el ingeniero (2026-07-08, «el codegen fue un error… debió ser modelo fundacional + piezas hechas por otros ingenieros»); analiza y documenta el orquestador |
| Generaliza / revisa | ADR-012 (tech=plan como dato → ahora puede fijar frameworks de comunidad) · ADR-017 (verificar-no-revisar baja UN NIVEL: del sustrato al producto) · reevaluación honesta 2026-06-25 (REVISA su claim «moat = re-derivación provable» → moat = verificación-del-artefacto) · ADR-022 §1 (regla espejo: congelar-con-pin, no podar) |
| Referencia | `factories/full-stack-kotlin/docs/work/FSK-FRONTEND-DESIGN-INCREMENT.md` (diagnóstico disparador, con ojos reales) · `../dataset_agent_re` (prueba externa del harness) |

## Contexto (medido, no narrado)
1. **El diagnóstico disparador (2026-07-08, screenshots del app vivo):** tras ~12 increments de arco
   frontend (list→detail→edit→operations→dashboard→styles→vercel→table→search→tabs→trash→login), la UI
   generada de snipeit tiene forms SIN labels, tablas de 24 columnas con overflow y «null» literal, sin
   app-shell. **Doce increments de evolución de templates producen menos calidad que un Django admin de
   2010, que es gratis.** No es falta de increments: es el TECHO de los templates.
2. **La gramática ya tocó la realidad y perdió:** el RBAC real de Snipe-IT es INEXPRESABLE en FSK
   (aproximación a 4 roles admitida en su `product.yml`); Snipe-IT costó 17 increments ADOPT y fue
   demovido a techo-de-regresión. Crecer una gramática hasta cubrir la realidad = construir un Rails
   peor, con UN mantenedor.
3. **La economía medida apunta al mismo lugar:** delegación honesta 22% en Fase 2 SOTA (el resto era
   columna/sustrato = ingeniería del pseudo-framework); opus-share 89% en el eje FSK medido
   (`DELEG-PAYOFF`), 49.7% en la mejor corrida S2 (KPI ≤35% aún rojo). Las horas-Opus — la restricción
   vinculante real (ADR-022 D-6) — se van al framework, no al producto.
4. **La prueba externa:** `../dataset_agent_re` se construyó con meta-factory SIN fábrica específica y el
   resultado fue excelente. Transfirió el harness (hooks, verificación por bloqueo) y la memoria
   documental (`docs/{STATE,LOG,decisions,work,reference}` — verificado: el esquema está verbatim en ese
   repo). Transfirió CERO codegen. **El activo portable es el PROCESO, no la emisión.**
5. **El análisis de los dos frentes** (el que fijó la decisión): el codegen determinista de templates
   pelea a la vez (a) contra los frameworks existentes en su propia cancha —0-modelo, regeneración
   barata— donde Rails/Django/Spring amortizan miles de horas-ingeniero que acá paga una persona, y
   (b) contra el modelo de frontera en capacidad — el LLM ES un codegen universal, mantenido por
   Anthropic, que mejora gratis; un template nunca va a tener criterio de diseño. La ironía: el nivel
   meta YA usa la arquitectura correcta (ADR-017: el LLM genera, los gates verifican) mientras FSK, un
   nivel abajo, seguía generando con templates.

## Decisión
1. **Re-definición de fábrica.** Una fábrica ES: gramática de spec (ADR-012) + **perfil de verificación**
   (estaciones-como-CHECKS, RTM, CI hermética, benchmark) + memoria documental. La **generación es
   model-nativa bajo el harness** (slots `generate-slot` acotados, gates deciden, veredictos — ADR-017
   aplicado al producto). Dato clave que lo hace barato: en FSK solo s0 y s6 GENERAN archivos; el resto
   de las estaciones ya son checks puros y se reusan tal cual sobre cualquier implementación.
2. **Reuso comunitario en fase de spec.** Al planificar/especificar, la pregunta OBLIGADA antes de
   construir es: «¿qué pieza ya validó la comunidad con miles de horas-ingeniero?» (frameworks, design
   systems, librerías). La spec las fija como DATO (extiende ADR-012). No volver a hacer determinista lo
   que por definición debió ser modelo fundacional + piezas de otros ingenieros.
3. **El codegen de templates queda CONGELADO** (`factories/full-stack-kotlin/codegen/scaffold/` y
   análogos): cero increments nuevos de evolución de templates. Regla espejo de ADR-022 §1:
   congelar-con-pin, NO podar — los productos existentes pineados siguen verdes gratis
   (`ci --rederive`). Volver a alimentarlo = acto deliberado con ADR y motivo escrito.
4. **El trade-off, con nombre (la pérdida honesta).** Se renuncia a la re-derivación bit-a-bit como moat
   (revisa la claim de la reevaluación 2026-06-25). El moat pasa a ser: spec + gates + artefacto PINEADO
   — re-VERIFICAR el artefacto sigue siendo determinista; re-DERIVARLO idéntico ya no. Para correctitud,
   auditoría y regresión — todo propósito que importa — verificar-el-artefacto ≥ re-derivarlo. El código
   deja de ser desechable; lo mantiene el modelo bajo gates (como todo el SWE agéntico serio, incluido
   dataset_agent_re).
5. **Primer increment de ejecución = experimento A/B falsable (ANTES de cualquier limpieza).** Frontend
   de `helpdesk` (vehículo sweet-spot): **brazo A** (control, ya documentado) = el plan de 5 INCs de
   templates de `FSK-FRONTEND-DESIGN-INCREMENT.md`; **brazo B** = UN slot LLM que genera el frontend
   desde la spec bajo los MISMOS gates s9 (Chromium real) + design-floor + screenshot en §Evidencia.
   Jueces: tokens+horas (los de ADR-022) · calidad (gates + ojos del ingeniero) · mantenibilidad (costo
   del cambio SIGUIENTE). El resultado calibra el ALCANCE del pivote: full model-nativo vs híbrido
   (esqueleto estructural determinista congelado + toda la superficie humana model-nativa).
6. **La limpieza es POSTERIOR y gateada por §5.** Hoy no se borra nada; se deja de alimentar. El backlog
   de evolución de templates (incluidos los 5 INCs del plan-control) queda DIFERIDO salvo que A gane el
   experimento — predicción registrada: gana B.

## Consecuencias
- **Doctrina de costos, un punto cambia:** «la línea de fábrica es 0-modelo» deja de ser la palanca de
  GENERACIÓN — el costo marginal por producto sube de ~0 a tokens-de-Sonnet-bajo-gates; a cambio el costo
  FIJO del pseudo-framework (horas-Opus) cae en órdenes de magnitud. A N chico la matemática domina a
  favor; la fila DÍA-A-DÍA del runbook (ADR-021) sigue válida para RE-VERIFICAR (pins/checks, 0-modelo).
- **F1 (regenerar ASF) se re-enmarca:** regenerar = generar model-nativo bajo el perfil de verificación
  de su spec, no re-correr templates.
- **Las horas FSK no fueron pérdida:** fueron el vehículo de dogfooding que templó el harness (hooks,
  verifier, delegación, dial, benchmark) — el activo que dataset_agent_re reusó gratis. El error habría
  sido SEGUIR invirtiendo horas marginales en templates a retornos sublineales.
- **Higiene de prefijo (ADR-021e):** el ajuste de reglas vivas (CLAUDE.md «Estado»/runbook, ROADMAP)
  viaja con el increment del experimento, no con este ADR.
