<!-- meta:doc sha=87189a86a9ee2a5654c41a610b973813f71a09b1 updated=2026-07-04T03:48Z -->
<!-- meta:doc sha=PENDING updated=2026-07-04T03:45Z -->
# COUNCIL-360-AUDIT — vista total: 15 sillas + topología de ejecución

> tipo: reference (estable) · creado: 2026-07-04T03:45Z · sesión S1 (Fable 5, pedido explícito del
> ingeniero: «pensar desde muchísimos ángulos, abogado del diablo y defensor»). Complementa
> `FOUNDATIONS-REAUDIT.md` (fundamentos vs conducta); esto es el barrido 360° + la auditoría de
> topología de ejecución. Los HECHOS citados se midieron en esta sesión (journal, filesystem, greps).

## §0 · Alcance declarado (resuelve la Silla 4)
**Académico por ahora** — monetización/clientes FUERA de alcance (declaración del ingeniero,
2026-07-04). La bandera elegida: **artefacto-tesis + doctrina publicable**, no producto comercial.

## §1 · El consejo — 15 sillas (una línea por silla; el detalle vivió en la sesión)
1. **Historiador**: el cementerio CASE/MDA/«Software Factories» murió de 3 muertes; el LLM mata la #3
   (extender el generador ya es barato: helpdesk first-try, 0 incrementos) y ADR-011 la #2; la #1
   (spec-complexity creep) sigue VIVA y sin vigía. Falsificador: spec-LOC → código-LOC.
2. **Científico experimental**: TODAS las mediciones son autorreferenciales — **falta el grupo de
   control** (CC pelado + revisión humana, mismo spec, $ + horas + defectos). El benchmark ya puede
   arbitrarlo (~1 día, ~$20). El experimento más valioso sin correr.
3. **Arquitecto de datos**: HECHO — todo producto tiene SOLO `V1__init.sql`; no existe V2 en el
   sistema. «Regenerar > mantener» hoy vale solo SIN estado de producción. Falta `SPEC-EVOLUTION`
   (spec-diff → migración generada + gate «los datos sobreviven»).
4. **Economista**: 133 incrementos (71 meta + 62 fábrica) → ~8 productos → 0 usuarios; sin señal de
   demanda no hay gradiente de VALOR (todos los KPIs son de costo). Mitigado por §0.
5. **Estratega**: el moat (re-derivación demostrable) vale ORO en software regulado/auditable, no en
   CRUD-race-to-bottom. Con §0: la «venta» es la tesis/paper.
6. **Ing. de seguridad**: circularidad del trust-chain — el modelo revisa la columna que el modelo
   escribió; el humano-raíz aprueba lo que declara no entender del todo. SAFE-8 se invierte de facto.
   Mitigación barata: red-team con instancia fresca sin memoria; auditoría externa (la defensa de tesis).
7. **Epistemólogo**: el vocabulario («medido», «verificado») lava n=1 como certeza; «app verificada» =
   pasó gates declarados, tasa de escape de defectos DESCONOCIDA. Disciplina: «medido(n=1)» vs
   «medido(re-derivable)».
8. **Ergónomo**: el cuello de botella emergente es el MODELO MENTAL del principal (evidencia: esta
   sesión — pasos entre líneas, INDEX invisible, operatoria opaca). Falta one-pager de operador
   REGENERABLE; cada «¿cómo funciona X?» del ingeniero = señal de defecto, como una compactación.
9. **Biólogo**: linaje único, selección auto-administrada = riesgo de máximo local; nunca corrió un
   diseño competidor. El clon-limpio + benchmark hacen barato el torneo de variantes.
10. **SRE**: acople total a plataforma (ya mordió: rename Task→Agent rompió la métrica en silencio) y
    a la LISTA DE PRECIOS (ADR-021). Falta canario de plataforma (check que afirme primitivas vigentes).
11. **Contador de atención**: el ledger precia tokens, no horas-humano (262 session_starts/3 semanas);
    wall-clock por sesión al `meta outcome` es gratis (timestamps ya existen).
12. **Minimalista**: journal — 5478 station_run · 262 session_start · **15 delegation · 3 compact ·
    1 recall · 0 graph_query**. El grafo («keystone») y el harness de delegación tienen ROI realizado
    ≈ 0; la corrida S2 pendiente es su juicio. La ley de la casa (medir o borrar) aplica a las joyas.
13. **Defensor**: (a) funciona de punta a punta re-derivable en clon limpio — casi nadie puede;
    (b) gates de dos lados = contribución metodológica genuina (mata la trampa PWF); (c) el sistema NO
    se miente a sí mismo (N/A-por-medición, HONEST-STATE, F1 matizado) — la propiedad más rara;
    (d) economía de cache SOTA; (e) validación convergente (opusplan, Spec-Kit).
14. **Arqueólogo 2036**: el código no sobrevive; la DOCTRINA puede — destilarla standalone
    (paper/informe) sería además la PRIMERA verificación EXTERNA del sistema (el gate faltante de más
    alto nivel: ojos ajenos).
15. **Pedagogo**: valor ya entregado independiente de mercado — el artefacto operacionaliza más SWE
    real que la mayoría de los codebases industriales; como proyecto de Integración, sobre-entrega
    exactamente lo que las rúbricas premian: evidencia.

**Veredicto:** el sistema es un espejo perfecto de sus propios criterios — corrige con disciplina
rarísima todo lo que sus instrumentos ven; acumula en silencio lo que queda fuera (usuarios, ojos
externos, comprensión del principal, datos de producción). No es «botar y simplificar»: es **girar los
instrumentos hacia afuera**.

## §2 · Topología de ejecución (auditoría con hechos, 2026-07-04)
- **Modo operativo real = WORKSPACE desde la raíz meta** (modelo Nx/Bazel/Rails-engine — SOTA-
  consistente, pero NO declarado en ningún doc). Todo corre con cwd=raíz: columna máxima activa,
  hooks de cierre-de-turno cwd-relativos, verbos `meta`.
- **CLAUDE.md de fábrica = medio-vivo**: la plataforma adjunta CLAUDE.md anidados al LEER archivos del
  subárbol (verificar con `/context` en sesión que toque FSK — canario de 30s); la prosa cabalga a
  demanda. **El harness de fábrica (.claude/ agents·hooks·skills·settings + seed propio) está DORMIDO**:
  solo se activa lanzando `claude` DENTRO de la fábrica (hooks con rutas RELATIVAS lo delatan), cosa que
  hoy nadie hace ni funciona con los gotchas de cwd. Misma clase que el grafo: construido-pero-dormido.
- **Deriva de doctrina entre niveles (hallazgo serio)**: FSK/CLAUDE.md aún dice «el cerebro es el
  orchestrator (Opus)» — pre-ADR-021; el runbook de costos nunca se propagó a las 5 fábricas. La
  doctrina fluye solo al EMITIR y después rota; la remediación conocida (re-emit total) PISA docs de
  fábrica (gotcha). Falta: emit acotado de harness o check de paridad de doctrina.
- **Exportar una fábrica → HOY se exporta el monorepo, por diseño declarado** (el `external_ci.yml` de
  FSK: «el checkout es el repo del Meta-Factory»). Acoples: FSK importa `metafactory` en 4 módulos
  (las otras 4 fábricas: 0 imports — pero todas necesitan el engine como RUNNER de la línea). La
  historia de confianza para un colega ya es de primer nivel: `git clone` + `meta ci --rederive
  --factory X` = re-deriva el pin en SU máquina (provenance estilo SLSA/in-toto casero). Opciones si
  aparece el colega real: (1) compartir monorepo (hoy, suficiente); (2) `meta export <fábrica>` —
  bundle standalone con engine vendoreado+pineado, gate = el bundle re-deriva == pin (reusa `ci`);
  (3) engine como pip package (sobredimensionado para §0). YAGNI hasta que exista el colega.
- **«Meta raíz = lugar más seguro» → SIGUE VERDADERO, con base formal**: columna máxima (fábrica ⊊
  meta, ADR-018 `least_priv`) + cierre-de-turno solo funciona ahí + settings portables
  (`$CLAUDE_PROJECT_DIR`, sin rutas absolutas). Matices: más-enforzado ≠ más-aislado (una sesión raíz
  toca TODO; la jaula por-fábrica sería el bundle exportado); consultas triviales pagan el alquiler del
  CLAUDE.md meta → día-a-día = shell directo/Sonnet (runbook).
- **Menores**: doble residencia posible (meta + FSK CLAUDE.md adjunto) — nadie mide la SUMA (el gate
  `agent_shadow` mide solo el de fábrica); concurrencia de 2 sesiones choca en `.proof/active.json`
  (conocido); Playwright cache es máquina-local (documentado).

## §3 · Cola consolidada de experimentos/acciones (ordenada por valor/costo)
1. **E1 — grupo de control**: CC pelado vs fábrica, mismo spec helpdesk, arbitrado por el benchmark
   (~1 día). Decide la historia de VALOR del sistema entero.
2. **E2 — `SPEC-EVOLUTION`**: spec v2 → migración generada + gate «los datos sobreviven». Decide
   «regenerar > mantener» para sistemas CON estado.
3. **Corrida S2 pendiente** (KPI opus-share) — además es el juicio del harness de delegación (Silla 12).
4. **One-pager de operador regenerable** (Silla 8) + `SESSION-CLASS-AS-DATA` (ya diseñado, DIFERIDO).
5. **Paridad de doctrina meta↔fábricas** (deriva ADR-021) vía emit acotado o check — NO re-emit total.
6. **Observers gratis**: horas-humano al ledger · fact `graph_query` al journal · suma de residencia
   de CLAUDE.md anidados · ratio spec-LOC/generado-LOC (muerte #1 de MDA).
7. **E3 — red-team de columna con instancia fresca** (Silla 6) · canario de plataforma (Silla 10).
8. **Declarar el modo workspace** en un doc de referencia (una sección, no maquinaria).
9. **La destilación standalone de la doctrina** (paper/informe de tesis) — la primera verificación
   externa (Sillas 14/15).
