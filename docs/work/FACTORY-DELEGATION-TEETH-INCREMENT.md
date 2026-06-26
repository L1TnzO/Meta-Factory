<!-- meta:doc sha=e6e66c077da4868c7b1e5a3bacfdc2d37f923c2a updated=2026-06-26T23:45Z -->
# Incremento FACTORY-DELEGATION-TEETH (escindido de HARNESS-DECOUPLE Fases 3–4)

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-26 ✅; reabierto y cerrado en una sesión — ver §Evidencia).
> Para ejecutar: poné el banner en abierto a mano (editá el campo de estado de este header — un `.md` siempre
> es editable; NO uses `meta increment open`, que rehúsa pisar un doc que ya existe) y confirmá con
> `meta increment status`. (El header dice DIFERIDO a propósito: la ley del lifecycle sólo cuenta como abierto el
> marcador canónico, así que este doc no ocupa el slot meta mientras espera.) **Autoridad: ADR-018** (§ delegación
> least-priv abajo). Es la mitad-de-teeth de ADR-016 Fase 2 §1; la mitad-de-fundación (`column_parity`) ya la
> entregó `HARNESS-DECOUPLE`.

## Por qué se escindió (no es deuda escondida)
`HARNESS-DECOUPLE` tenía dos capacidades distintas bajo un slug: **(a)** la columna de fábrica es una proyección
fiel de un único source (drift = rojo) — *fundación*; **(b)** la columna de fábrica además **lleva el enforcement
de delegación** (`blast_radius`/`verdict_required`) y `agent_shadow` lo reconoce con diente a nivel fábrica —
*propagación de teeth*. (a) está entregada y verde (`column_parity`, ADR-018 §1). (b) es trabajo genuinamente
separable y NO se cumplió → se baja acá en vez de declararse hecho. La fundación es exactamente lo que (b) necesita
para no driftear cuando se proyecte.

## Objetivo
Cerrar el hueco de **I-12 a nivel fábrica**: hoy `blast_radius`/`verdict_required`/`gate_guard` viven SÓLO en el
meta-vivo (frontmatter del `generator`, Fase 2 DELEGATION-HARNESS); la columna PROYECTADA a la fábrica no los
carga, así que una prohibición de un agent de fábrica no tiene sombra real. Propagarlos por la MISMA proyección
determinista que `column_parity` ya verifica (no copia a mano), acotados least-privilege a los slots de cada nivel.

## Fases (heredadas de HARNESS-DECOUPLE 3–4)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **Propagar el enforcement de delegación a la fábrica, least-priv.** `blast_radius`/`verdict_required` en la columna proyectada de fábrica, acotados a sus slots; cableados per-agent (NO en `settings.json` — ver §Evidencia). Debe pasar `column_parity` (la proyección, no copia). | ✅ |
| 2 | **I-12 con diente abajo.** `agent_shadow` a nivel fábrica: una prohibición de un agent de fábrica tiene sombra REAL (instalada + cableada). Negativo no-decorativo: borrar el target → rojo, aislado. | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. La columna proyectada de cada fábrica carga `blast_radius`/`verdict_required` acotados a sus slots, y
   `column_parity` sigue VERDE (se propagó por proyección, no a mano → no introdujo drift).
2. `agent_shadow` a nivel fábrica reconoce la sombra de una prohibición declarada de un agent de fábrica;
   negativo probado: borrar el target → rojo, sabotaje aislado (sólo ese check).
3. `ci --rederive` de cada fábrica == su pin (re-pin honesto y narrado si la columna proyectada cambió bytes).
4. `meta check` N/N verde; single-source intacto (la ley en `seed/`, la columna NO spec-driven, ADR-018 §4).

## Evidencia (2026-06-26 · cerrado por bloqueo)

**Raíz medida.** Los teeth (`blast_radius`=write-bounded · `verdict_required`=must-leave-verdict) vivían SÓLO
en el meta: su ley en `src/metafactory/delegation.py`, que una fábrica producida (sin `src/metafactory`) NO
podía cargar. Proyectados as-is quedaban INERTES (best-effort `except: return 0`) → contrato hueco abajo.

**Fase 1 — ley seed-canónica + columna proyectada.**
- `seed/delegation.py` NUEVO: la ley como Stage-0 seed (igual que `verifier.py`/`lifecycle.py`), `copy_seed`
  la propaga byte-idéntica a cada fábrica. `_seed.load_seed_delegation` (espejo de `load_seed_lifecycle`) +
  `metafactory.delegation` ahora re-exporta el seed → callers del meta intactos; single-source = el seed.
- Los 2 hooks cargan la ley de `seed/delegation.py` POR PATH (idiom clone-robust de `increment_guard`, cero
  `metafactory.*`) → REALES en ambos niveles. Probado en FSK con un slot vivo: write in-slot=exit0 ·
  out-of-slot=exit2 (mensaje) · sin verdict=exit2.
- Columna re-materializada (M1, `meta station m00→m01`) en las 5 fábricas; `column_parity` VERDE
  (proyección, no copia; diente RED vivo).

**Fase 2 — diente I-12 a nivel fábrica.**
- `_emit_harness` (`codegen/renderer.py`, `_agent_fields`/`_delegation_wiring`) AUTO-cablea los teeth en todo
  agent que puede WRITE: bloque `hooks:` per-agent (PreToolUse→blast_radius · Stop→verdict_required) + las 2
  shadows I-12. SUBSTRATE-projected, NO spec DATA (ADR-018 §4): el spec declara el ROL, el sustrato decide el
  ENFORCEMENT; los read-only (reviewer/triage) no reciben nada (least-priv). Sólo el `writer` (sonnet) tiene
  Write → sólo él se cablea, en las 5 fábricas.
- `agent_shadow` reconoce el cableado PER-AGENT del frontmatter (`_frontmatter_wired_hooks`), no sólo
  `settings.json` → la sombra de delegación cuenta como CABLEADA viva. Negativo probado (clon hermético):
  borrar `blast_radius.py` → rojo «sombra inexistente», aislado. Tests nuevos en `tests/test_agent_shadow.py`.

**Decisión (desvío consciente del texto de Fase 1).** El handoff decía «wirearlos en el `settings.json`
proyectado»; se eligió cableado **per-agent** (frontmatter del `writer`), NO global: `blast_radius`/
`verdict_required` NUNCA son globales (patrón del `generator` meta) — globalizarlos los dispararía en la sesión
principal y en todo subagente. Por eso se extendió `agent_shadow` para reconocer el cableado per-agent.

**Colateral revertido (lección).** Re-emitir la línea meta completa in-tree para regenerar `writer.md`
(m07 gateado tras m00–m06) CLOBBEREA artefactos de fábrica no relacionados: docs de FSK (`STATE.md` −630
líneas, `LOG.md` −1276), `stations/s0.yml`·`s4.yml` (reformat/drift), y BORRA el skill `correr-app` (no está
en el spec FSK). Todo revertido con `git restore` → el changeset es SÓLO delegación. Lección: la re-emisión
de harness in-tree no es quirúrgica por estación; para tocar sólo agents conviene un emit acotado a agents.

**Cierre.** `meta check` 14/14 · suite + tests nuevos verdes · las 5 fábricas `ci --rederive --all-products`
== pin (los productos no dependen de la columna/harness → intactos). Single-source intacto.

## Punteros
- `HARNESS-DECOUPLE-INCREMENT.md` — el núcleo entregado (`column_parity`) + la nota de descope.
- ADR-018 — la columna como proyección de un único source (least-priv por nivel).
- `DELEGATION-HARNESS-INCREMENT.md` (Fase 2 SOTA) — el origen de `blast_radius`/`verdict_required` arriba.
