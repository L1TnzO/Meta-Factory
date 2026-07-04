<!-- meta:doc sha=6fe7ab1f63002f10f85eeda6ac0d975d3679955e updated=2026-07-04T20:46Z -->
# Incremento MUTATION-ESCAPE

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-04T20:32Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
E4/H-3 (COUNCIL-360 §6.4.5, ADR-022): convertir «app verificada» de claim a NÚMERO — el instrumento
de **tasa de escape** (mutation testing v1: mutantes de un-operador, deterministas por seed, con
restauración garantizada) + las DOS campañas medidas: (a) el producto helpdesk contra sus gates
reales (s1·s5·s9 sin re-scaffold — estaciones de checks puros), (b) el propio motor
(`verify/checks/`) contra `tests/` — la fuerza del guardián mismo.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Slot `mutation-escape` delegado: `verify/mutation.py` (sites→select→apply→gate→restore, byte-verify en finally) + tests dos-lados herméticos | ✅ |
| 2 | Campaña MOTOR: mutantes en `verify/checks/{kind_hygiene,security_scan,declared_deferred}.py`, gate = suite completa | ✅ |
| 3 | Campaña PRODUCTO: mutantes en el Kotlin generado de helpdesk (`AppServer.kt`), gate = compile + 5 route_check de s5 (+1 muestra viva s9 completa) — cero regeneración | ✅ |
| 4 | Los números al árbol: tasa de escape por campaña + sitios escapados (los defectos que los gates NO ven) acá en §Evidencia | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `.gen/mutation-escape.verdict.json` green (acceptance = suite completa exit 0).
2. §Evidencia abajo tiene DOS tasas de escape re-derivables (comando exacto + seed fijo — cualquiera
   las re-corre y obtiene los mismos mutantes).
3. Un escape NO es fracaso: es la medición que la Silla 7 pidió — se registra tal cual y alimenta
   la cola de gates futuros.

## §Evidencia (medido 2026-07-04, seed=7 — re-derivable con los comandos exactos)

### Campaña MOTOR — «¿tests/ mata al guardián mutado?»
`PYTHONPATH=src python3 -m metafactory.verify.mutation src/metafactory/verify/checks/<t>.py python 6 7 -- python3 -m pytest -q -x tests`
| target | tested | killed | escaped | tasa de escape |
| --- | --- | --- | --- | --- |
| `kind_hygiene.py` | 6 | 6 | 0 | **0.000** |
| `security_scan.py` | 6 | 6 | 0 | **0.000** |
| `declared_deferred.py` | 2 | 2 | 0 | **0.000** |
**Motor: 14/14 muertos — 0% escape** (set v1 de operadores, N=14: la suite guarda al guardián).

### Campaña PRODUCTO — helpdesk vs compile+contrato-estático (gate: gradle compileKotlin + los 5 route_check de s5)
`PYTHONPATH=src python3 -m metafactory.verify.mutation factories/full-stack-kotlin/products/helpdesk/build/product/src/main/kotlin/webapp/endpoints/AppServer.kt kotlin 8 7 -- bash <gate>`
- tested=8 · killed=2 · escaped=6 → **tasa de escape 0.750** (sitios: L389·L439·L441·L442·L504·L567 —
  todos flips `&&/||`/`==/!=` en el DISPATCH de rutas del `when`).
- Lectura: los gates estáticos verifican el CRUCE contrato↔código (topología/roles/mutabilidad), no la
  lógica interna del dispatch — la clase exacta de defecto que VISION §5.2 declara fuera del alcance
  de los gates. El número convierte esa calibración de prosa a medición.

### Muestra VIVA — 1 escapado (L441 `&&`→`||`) contra `access_control_live` COMPLETO (server real + PG + ~70 probes)
**SOBREVIVIÓ (proof exit 0)**: el orden de ramas del `when` enmascara el flip (las ramas previas
capturan primero) → mutante ~equivalente en la superficie ejercitada. El escape es REAL, no artefacto
del gate parcial. Restauración verificada (baseline re-verde tras revertir).

### Los números de la Silla 7 (honestos)
1. **Motor 0% escape** (N=14) · 2. **Producto 75% escape vs estáticos** (N=8; cota SUPERIOR respecto
del stack completo) · 3. **≥1 escape confirmado contra el stack VIVO completo** — «app verificada»
significa: verificada EN la superficie que los gates ejercitan; el residuo ahora tiene número y clase
(dispatch interno). Follow-up con gatillo: si un eje futuro toca el dispatch del server generado, la
campaña viva completa (8 mutantes × s9) entra ANTES del merge.
