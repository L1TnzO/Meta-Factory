<!-- meta:doc sha=1c863816d0e2857703ac66a6d608ca9c785a2096 updated=2026-06-17T15:54Z -->
# Incremento MAT-2-LIVE-GEN

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-16T23:26Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo

Ejercer **por primera vez** el seam creativo con un **LLM VIVO**: `via = claude -p` (ADR-013) genera
**lógica de dominio REAL** (no scaffold estructural, no stub) bajo gate, en **dos dominios** (Full-Stack TS
y ASF Python) por el MISMO kind (principio #6). Reconcilia el no-determinismo con SAFE-3 (§7 del
MATURITY-PLAN): el artefacto ACEPTADO se **PINEA** (se committea = es la fuente desde entonces);
`ci --rederive` (clon limpio) **re-verifica el pin SIN regenerar** (determinista, sin llamar al LLM).

## Diseño (el porqué)

- **El seam YA EXISTE** (C1/ADR-013): `generate` soporta `skip_if_exists: true` con la semántica EXACTA de
  §7 (`renderer.py` docstring: *"don't re-invoke the generator if the slot is already filled, e.g. a
  non-deterministic LLM"*). MAT-2 **no construye sustrato** — lo EJERCE con un LLM real. `git diff
  src/metafactory/` = **0 líneas** otra vez (anti-overfit, §5).
- **El split §7, mecánico**: `via = claude -p` + **dest committeado** (no bajo `build/`, gitignored) +
  `skip_if_exists: true`. 1ª gen (artefacto ausente) → llama al LLM → gate verifica → **lo committeo**
  (pin). Re-derivar (clon limpio): el artefacto pineado está presente → el slot SALTA el LLM → el gate
  re-verifica el pin → verde, determinista, sin auth/red en CI.
- **El anti-patrón "domain vacío" (de F1) AHORA bloquea**: el gate es un **contract test** que EJERCITA la
  lógica generada con entradas/salidas concretas. Un stub (`return {}`) → test rojo. El LLM tiene que
  implementar de verdad para pasar. El test + `package.json` se EMITEN deterministas (acción `write`); el
  ÚNICO artefacto no-determinista/pineado es la lógica generada.
- **La tech del LLM vive en la fábrica** (ADR-012): un wrapper `codegen/gen_llm.py` (lee el brief, corre
  `claude -p`, extrae el código, escribe el dest) es el `via`. El sustrato no nombra `claude`.
- **Co-validación (2 dominios, mismo kind)**: Full-Stack → `summarizeTodos` (agrega/filtra, TS, gate
  `node:test`). ASF → `merge_findings` (reducer dedup por confianza, Python, gate `pytest`).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Wrapper `gen_llm.py` (via=claude -p) + Full-Stack: estación s3 live-gen `summarizeTodos` (brief en spec, test+pkg.json emitidos, dest committeado, skip_if_exists). 1ª gen VIVA → gate verde → commit del pin | ✅ 2026-06-17T15:37Z |
| 2 | §7 por bloqueo: `ci --rederive` verifica el pin SIN llamar al LLM (determinista) · corromper el pin → gate rojo · stub → contract test rojo | ✅ 2026-06-17T15:41Z |
| 3 | ASF co-validación: live-gen `merge_findings` (Python) por el MISMO kind; gate `pytest`; 1ª gen viva → commit del pin | ✅ 2026-06-17T15:48Z |
| 4 | Docs (STATE/ROADMAP/MATURITY-PLAN + evidencia) + cierre; dummy intacta; `meta check` verde | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. Un producto cuya lógica de dominio se **GENERÓ por `claude -p`** (no se templateó) pasa su contract test
   en su toolchain, en **2 dominios** (TS + Python) por el MISMO kind. La 1ª generación fue VIVA (log del LLM).
2. **§7**: `ci --rederive` re-verifica los artefactos PINEADOS == pineado, **sin** invocar el LLM (clon
   limpio, sin auth). Corromper un pin → su gate rojo. Un stub no pasa el contract test.
3. `git diff src/metafactory/ + seed/` por MAT-2 = **0 líneas** (el seam ya existía; se ejerció).
4. dummy/ASF previos intactos; congelado intocado; `meta check` verde.
