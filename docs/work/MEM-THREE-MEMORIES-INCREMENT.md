<!-- meta:doc sha=0907b5bbeb1e6243d9c57b4447fa5f40990a90c0 updated=2026-06-26T21:51Z -->
# Incremento MEM-THREE-MEMORIES

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-26T21:43Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Cerrar **M6** de MEMORIA v2 (ADR-019): MEDIR el solapamiento entre las tres memorias del harness
(CLAUDE.md curado · note-store de auto-memoria `~/.claude/.../memory/*.md` · wiki `docs/`), DECIDIR con el
dato la autoridad single-source (ADR-007 regla 3) y DEGRADAR una copia a puntero. Deja MEMORIA v2 completa
salvo la regla de escape (§6).

## Contexto (por qué — la cadena completa en ADR-019 §5/§Consecuencias)
ADR-019 nombró las tres memorias como un **solapamiento medible**, no resuelto por intuición: un riesgo de
tercer-drift (los notes `project` re-narran lo que `docs/` ya posee) + un costo fijo/sesión (MEMORY.md se
inyecta en cada arranque). M6 lo CIERRA con la medición que M5 habilitó. Hallazgo (re-derivable, ver §Evidencia):
de 17 notes — **6 `feedback`** (~17 KB: cómo trabajar + gotchas; el single-source LEGÍTIMO de la auto-memoria,
`docs/` no lo tiene ni debe) · **9 `project`** (~142 KB, dominados por `fsk-s16` 79 KB: NARRAN estado/historia
del proyecto = lo que `docs/STATE.md`+`LOG.md`+`work/` ya poseen → la superficie de drift) · **2 `reference`**.
El note-store `project` viola el **propio protocolo de memoria del harness** («no guardes lo que el repo ya
registra»).

## Regla single-source decidida (ADR-007 regla 3 sobre tres memorias)
- **`docs/` (wiki)** = autoridad de **HECHOS del proyecto** (estado · historia · decisiones · roadmap ·
  evidencia por incremento). Re-derivable, sellada (ADR-009), git-versionada.
- **CLAUDE.md** = autoridad de las **REGLAS de ruteo de la fase viva** (las normas operativas de hoy).
- **note-store de auto-memoria** = autoridad SÓLO de lo que `docs/` no tiene ni debe: la **relación
  cross-sesión** — quién es el ingeniero + cómo quiere que trabaje (`feedback`) + referencias externas
  (`reference`). NO debe narrar estado del proyecto (`project` = el anti-patrón). Un hecho de proyecto en la
  auto-memoria degrada a un **puntero** (la línea-índice de MEMORY.md alcanza).
- **Por qué la auto-memoria NO lleva diente de `meta check`** (a diferencia de M1/M3, que gobiernan el STATE
  IN-tree): vive FUERA del árbol git (`~/.claude/...`), es por-usuario/por-máquina y AUSENTE en un clon limpio.
  Cablearla a `meta check` rompería la portabilidad clon-limpio-verde del proof. Su gobierno es la REGLA +
  una **medición re-derivable on-demand** (`overlap.py`, observador puro), no un gate.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `memory/overlap.py` — medición determinista (shingle-containment, cero modelo) de cada note vs `docs/`, clasificada por `type`; localiza la mem-dir best-effort y DEGRADA con gracia si ausente (portabilidad) | ✅ |
| 2 | Readout `meta metrics --overlap` (corre la medición si la mem-dir está; nota de una línea si no) + `tests/test_overlap.py` dos-lados (rida la `suite`, no es gate) | ✅ |
| 3 | DECISIÓN declarada: reconciliar `reference/MEMORY-ARCHITECTURE.md` con la regla single-source + razón observador-no-gate | ✅ |
| 4 | APLICAR: degradar el note más puro de duplicación (`metrics-gaps…`, hoy poseído por ADR-019/roadmap/STATE) a un puntero; contrato single-source en el header de MEMORY.md; memoria `feedback` con la regla | ✅ |

## Evidencia (re-derivable)
- **Medición (Fase 1+2).** `meta metrics --overlap` sobre los 17 notes pre-decisión:
  `feedback×6 · project×9 · reference×2 · MEMORY.md 3458 tok`; containment literal vs `docs/` (k=5): **0 alto · 2 medio
  · 15 bajo** (máx 0.206 `f1-asf-regenerate-not-v2`; `fsk-s16` 79 KB = **0.004**). **Hallazgo que CAMBIÓ la acción:**
  los `project` PARAFRASEAN `docs/`, no lo copian → el riesgo es semántico, no copy-paste → governance hacia-adelante,
  NO purga (la medición la desaconseja). Ausente la mem-dir (clon limpio/CI), el readout imprime **una línea honesta**,
  no rompe — la portabilidad clon-limpio del proof se preserva.
- **Tooth dos-lados (Fase 2).** `tests/test_overlap.py` 15/15: un note COPIADO de `docs/` → containment 1.0 → banda
  HIGH (muerde); un note único → 0.0 → LOW (no muerde); frontmatter excluido; mem-dir ausente → `find_memdir`=None
  (degrada). Rida el check `suite` → `meta check` sigue **14/14** (observador, no gate nuevo).
- **Decisión declarada (Fase 3).** `reference/MEMORY-ARCHITECTURE.md §8.2` — bloque `[CERRADO · ADR-019 / M6]`: la
  4ª costura `docs/`↔note-store + la regla single-source + el porqué observador-no-gate.
- **Aplicado (Fase 4) — puntero en vez de copia, re-medible.** `metrics-gaps-and-semantic-index-reframe.md`
  degradado a puntero (`type: project`→`reference`, cuerpo = punteros a ADR-019/roadmap/STATE/HONEST-STATE);
  contrato single-source en el header de `MEMORY.md`; memoria `feedback` `three-memory-single-source`; puntero
  COLGANTE `r1-product-instance-done.md` (archivo inexistente) removido del índice. Post-decisión:
  `feedback×7 · project×8 · reference×3 · MEMORY.md **3458→3145 tok**` (la línea-índice gigante → puntero).

## Criterio de cierre (demostrable, no narrable)
1. `meta metrics --overlap` imprime la métrica de solapamiento por note (containment + banda + `type`) y
   degrada con gracia cuando la mem-dir no existe (portabilidad: no rompe en clon limpio).
2. `tests/test_overlap.py` es dos-lados: un note sintético COPIADO de `docs/` cae en banda alta (flagueado);
   un note único cae en banda baja (no flagueado). Rida el check `suite` (`meta check` sigue 14/14).
3. La regla single-source queda DECLARADA en `reference/MEMORY-ARCHITECTURE.md` (autoridad de diseño).
4. Existe **un puntero en vez de copia**: el note `metrics-gaps-and-semantic-index-reframe.md` degradado a
   puntero a `docs/` + su línea de MEMORY.md actualizada; contrato single-source en el header de MEMORY.md.
5. `meta check` verde; árbol limpio; STATE «Ahora» refleja M6 ✅ (MEMORIA v2 completa salvo §6); LOG con episodio.
