<!-- meta:doc sha=a0fe3e0c87d64475efa54d55431fcf8a0374a340 updated=2026-07-03T23:01Z -->
# Bitácora — IoT Factory
> tipo: log · append-only, MÁS NUEVO ARRIBA · inmutable una vez escrito (esquema ADR-021).

## 2026-07-03 — `IOT-S1-FIELD-VOCAB` ✅ (eje R2 en Go, vehículo §5 de COST-DOWN)
Diseñado por S1 (Opus, contrato+gate+blast-radius fijados), ejecutado por S2 (Sonnet, `--agent orchestrator`)
vía `generate-slot` → `generator` (2 spawns). El codegen gana `type: enum` Go type-safe (`type <F> string` +
const-block + `Valid<F>` fail-closed + campo tipado) — mirror de `FSK-S11` en la 2ª cadena de herramientas
(Go), cross-validando la generalidad del eje R2. `fleet` adopta `Health` (no-requerido); demo `iotgw` queda
byte-idéntico. Diente de dos lados probado por sabotaje (`Valid` siempre-true → rojo, revertido → verde) y
confirmado por mí leyendo el test generado. `ci --rederive --all-products --factory iot` 2/2==pin (proof_sha
hashea `(station, checks exit)`, no contenido — el pin de `fleet` queda sin diff, por diseño PF-10, no un
bug). Anti-overfit: `src/`+`seed/` diff vacío; `scaffold_product.py` 665→760 líneas.
**Residuo real encontrado y corregido en vivo** (no un re-diseño): el manifest S1 no había abierto el
incremento de NIVEL PRODUCTO que `increment_guard` exige para `product.yml` (ADR-016 layering) → 1er spawn
devolvió ROJO honesto; se abrió `products/fleet/docs/work/IOT-S1-FIELD-VOCAB-FLEET-INCREMENT.md` (companion) +
se corrigió un bug real del manifest (`ci --rederive` sin `--factory iot`) → 2do spawn GREEN. Detalle completo:
`work/IOT-S1-FIELD-VOCAB-INCREMENT.md §Evidencia` + companion `products/fleet/docs/work/…-FLEET-INCREMENT.md`.
Pendiente para S3 (Opus, cierre): medir opus-share/$ de esta sesión (transcript
`d14b2cf6-035c-461b-96a8-3f6fdeb95a8d.jsonl`) contra el KPI de `COST-DOWN` §5.

## nacimiento — generada por el Meta-Factory
- La fábrica iot se construyó corriendo M0–M8 sobre su factory-spec. El sustrato no se
  escribió a mano: ascendió del template del Meta-Factory (los 13 invariantes), verificado por gate.
