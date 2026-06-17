<!-- meta:doc sha=8cb96f80c006517d72013454a74fabb405932ac8 updated=2026-06-17T16:01Z -->
# Incremento MAT-2-LIVE-GEN

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-17T16:01Z) (creado 2026-06-16T23:26Z). Cerralo con `meta increment close`
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
| 4 | Docs (STATE/ROADMAP/MATURITY-PLAN + evidencia) + cierre; dummy intacta; `meta check` verde | ✅ 2026-06-17T15:58Z |

## Criterio de cierre (demostrable, no narrable)
1. Un producto cuya lógica de dominio se **GENERÓ por `claude -p`** (no se templateó) pasa su contract test
   en su toolchain, en **2 dominios** (TS + Python) por el MISMO kind. La 1ª generación fue VIVA (log del LLM).
2. **§7**: `ci --rederive` re-verifica los artefactos PINEADOS == pineado, **sin** invocar el LLM (clon
   limpio, sin auth). Corromper un pin → su gate rojo. Un stub no pasa el contract test.
3. `git diff src/metafactory/ + seed/` por MAT-2 = **0 líneas** (el seam ya existía; se ejerció).
4. dummy/ASF previos intactos; congelado intocado; `meta check` verde.

## Evidencia (por bloqueo, no por prosa)
1. **Generación VIVA en 2 dominios, mismo kind** ✅:
   - Full-Stack **s3** → `claude -p` generó `summarizeTodos` (TS) — un `for` real que cuenta `total`/`done` y
     recolecta `pending` en orden; `product-run --factory full-stack` PASS (`domain_logic_contract`,
     `node --experimental-strip-types --test`). Commit del pin `6602330`.
   - ASF **s9** → `claude -p` generó `merge_findings` (Python) — dedup por `id` conservando la mayor
     `confidence`, orden desc; `product-run --factory agent-systems-factory` PASS (`domain_logic_contract_live`,
     `pytest`). Commit del pin `eef1853`. El `via` es `codegen/gen_llm.py` (en la FÁBRICA, ADR-012; el sustrato
     no nombra `claude`). El test+package.json/conftest se EMITEN deterministas (`write`); el único artefacto
     no-determinista/pineado es la lógica generada.
2. **§7 — pin re-derivable SIN LLM** ✅: con `claude` SABOTEADO en el PATH (fake que deja un testigo y sale 1,
   simulando "sin auth"), `ci --rederive` dio **full-stack 4/4** y **ASF 7/7 == pineado** en árbol limpio
   (ASF reconstruye el venv) y el **testigo quedó AUSENTE** ⇒ el generador nunca se lanzó (`skip_if_exists`).
   Pin corrompido (lógica incorrecta) → gate ROJO; **stub** (`return {}` / `return []`) → contract test ROJO,
   en ambos toolchains. Determinismo en la verificación, no en la generación (I-3); reconcilia SAFE-3.
3. **Sustrato intocado** ✅: `git diff 90d87ad..HEAD -- src/metafactory/ seed/` = **0 líneas**. El seam ya
   existía (C1/ADR-013, `renderer.py::_generate` + `skip_if_exists`); MAT-2 lo EJERCIÓ con un LLM real.
4. **Aislamiento + verde** ✅: dummy intacta (`ci --rederive` 5/5); ASF congelado (`../Agent_Systems_Factory/`)
   intocado; `meta check` **6/6** (suite `tests/` 451; el test de fidelidad S0–S8 actualizado: la línea
   canónica sobrevive íntegra + s9 explícita aditiva). m02 materializó SOLO `s9.yml` (sin churn en s0–s8).
