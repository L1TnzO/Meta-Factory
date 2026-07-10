<!-- meta:doc sha=9609e7533d4866755fbd5c08a3e3e5ff9735ec5a updated=2026-07-10T23:29Z -->
# Informe Final — estado de generación y guía de ensamblado

> Generado según `../../../Guia_Generacion_IA_Informe_Final.md` (formato UFRO + rúbrica 100 pts),
> redactado **asumiendo el sistema desarrollado** conforme a `../design/` (decisión del autor,
> 2026-07-04). Regla respetada: ningún dato/métrica/cita inventada — todo lo no disponible está
> marcado `[FALTA DATO: …]`.

## Orden de ensamblado (Anexo A de la guía)
Carátula → Comisión → (Dedicatoria/Agradecimientos) → **00-resumen-ejecutivo** → Índices →
**01-capitulo-1** → **02-capitulo-2** → **03-capitulo-3** → **04-capitulo-4** → **05-capitulo-5** →
Nomenclatura y Bibliografía (**06**) → Anexos. Figuras: `figuras/*.mmd` (Mermaid, elaboración
propia) — exportar a imagen al maquetar; numeración ya referida en el texto (3.1, 3.2, 3.3).
Formato de maquetación pendiente (carta, Calibri 12, interlineado 1,5, márgenes 2/3/2/2 cm,
capítulos en hoja aparte, numeración desde Cap. 1): se aplica al pasar a documento final.

## Nombres oficiales (coherencia terminológica — usar EXACTAMENTE estos en texto/figuras/video/repo)
ReqCouncil · Transcript Ingestor · Anchored Chunks · Blackboard · Council · Moderator ·
Functional/Data/NFR/Security & Compliance/UX/Integration Analyst · Gap Hunter · Conflict Detector ·
Evidence Skeptic · Consensus Protocol · Convergence Controller · Synthesizer · Traceability Store ·
HITL Checkpoint · Review Packet · Eval Harness · gates (E0–E4) · CCI.

## Autoevaluación por subcriterio (Anexo B; niveles: S=100% B=85% A=70% I=40% NE=0%)
> Actualizado 2026-07-06 (H6 cerrado — E0–E4 ejecutados, informe re-llenado con datos reales,
> Grupo C respondido por el autor). Único residual real: 5 citas secundarias de biblioteca.

| Sección (pts) | Nivel hoy | Qué la sube a S |
|---|---|---|
| Resumen (6) | **S** — cifras reales de E0–E4 + compromiso de honestidad citado | — |
| 1.1 Problema (4) | B — evidencia numérica real de los datasets | cita primaria Fit-Gap (residual biblioteca) |
| 1.2 Justificación (2) | S | — |
| 1.3/1.4 Objetivos (6) | S — verificables, trazables a Tabla 4.1 | — |
| 2.1 Fundamentos (3) | B — cada concepto conecta a decisión | 2 citas secundarias pendientes (REConSum/Connextra si se exigen) |
| 2.2 Fuentes+comparación (6) | **S** — 4 papers con autoría/año/DOI reales, 2 tablas comparativas | — (residual: REConSum/OntoAgent si el tribunal exige cita puntual) |
| 2.3 Justificación stack (3) | S — tabla tecnología→requisito→alternativa | — |
| 3.1 Metodología (3) | S — sin ceremonias adicionales, declarado | — |
| 3.2 Hitos+riesgos (3) | **S** — Tabla 3.1 con las 6 fechas reales + Tabla de riesgos con materialización medida | — |
| 3.3 Stakeholders (3) | **S** — Profesor Guía nombrado | — |
| 3.4 RF/RNF (4) | S — RF1–RF8, RNF1–RNF5 verificables, medidos en Cap. 4 | — |
| 3.5 Diseño+decisiones (5) | S — 3 figuras + 5 trade-offs explícitos | exportar figuras a imagen al maquetar |
| 3.6 Implementación (5) | **S** — 2 dificultades reales de integración documentadas | — |
| 3.7 Reproducibilidad (6) | **S** — `pyproject.toml` + `requirements.txt` pineado; repo local (sin remoto — declarado) | publicar remoto si el tribunal lo exige |
| 3.8 Seguimiento+DoD (3) | **S** — cambio de alcance real (H6 §9) documentado | — |
| 4.1 Entregable (5) | **S** — corrida de evidencia con números reales (41 requisitos, pin e1-h4-dsv4flash) | — |
| 4.2 Cumplimiento OE (4) | **S** — OE1–OE5 todos ✅ con evidencia | — |
| 4.3 Pruebas+métricas (7) | **S** — E0–E4 ejecutados, 4 tipos de prueba con números reales | — |
| 4.4 Línea base (4) | **S** — Tabla 4.5 12 celdas + compromiso de honestidad activado con números | — |
| 4.5 Análisis crítico (4) | **S** — 6 amenazas/limitaciones, incl. las medidas post-ejecución | — |
| 5 Conclusiones (6) | **S** — síntesis numérica + 2 aprendizajes reales + retrospectiva del autor | — |
| Figuras/tablas (8) | B — numeradas, anunciadas, interpretadas | exportar Mermaid a imagen final (única tarea de maquetación) |

## `[FALTA DATO]` residual — solo biblioteca, no bloquea el resto
Los 4 papers primarios de los datasets ya tienen autoría/año/DOI reales (2026-07-06). Quedan **5
citas secundarias de mención puntual** en el Cap. 2/1 (`06-bibliografia-nomenclatura.md`):
REConSum (RELabUU Utrecht) · OntoAgent (+33% IRE) · segmentación Fit-Gap · plantilla
Connextra/Cohn · literatura de debate multi-agente/overhead de tokens. Resolver solo si el
tribunal exige que cada mención puntual tenga cita propia.

## Cómo continuar
1. **Hecho (2026-07-06):** H1–H6 cerrados, Cap. 3/4/5 + Resumen + FICHA-MAESTRA re-llenados con
   datos reales re-derivados de `runs/pinned/**`, y el Grupo C (identidad/decisiones de autor)
   respondido — modalidad, Profesor Guía, cliente/curso, repo remoto, requirements.txt, reflexión
   personal.
2. **Hecho (2026-07-06): compilado a PDF real** — `Informe-ReqCouncil.pdf` (esta carpeta), 52
   páginas, formato Anexo A (hoja carta, márgenes 2/3/2/2, Carlito 12, capítulos en hoja aparte,
   numeración desde Cap. 1, índices auto-generados, figuras Mermaid ya renderizadas y embebidas).
   Pipeline reproducible + residuales exactos (qué es aproximado, qué campos `[COMPLETAR: …]`
   solo el autor puede llenar) en `build/README.md` — leer ahí antes de re-generar o entregar.
3. Pendiente, opcional: resolver las 5 citas secundarias de biblioteca si el tribunal las exige.
4. Maquetación final: revisar los `[COMPLETAR: …]` del PDF (nombre del estudiante, departamento,
   logo UFRO, comisión evaluadora — ver `build/README.md`) + checklist de coherencia (guía §14).
