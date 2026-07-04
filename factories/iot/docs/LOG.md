<!-- meta:doc sha=f60cc3c739ee1771159cd61a21ddd0bf59c480cd updated=2026-07-04T14:33Z -->
# Bitácora — IoT Factory
> tipo: log · append-only, MÁS NUEVO ARRIBA · inmutable una vez escrito (esquema ADR-021).

## 2026-07-04 — medición S3 del transcript de `IOT-S1-FIELD-VOCAB` (el pendiente del episodio de abajo)
Transcript `d14b2cf6-…` medido (dedup por `message.id`, 113 mensajes; precios `graph/pricing.py`, TTL 5m
por ley honesta): **$5.65 total** — opus-4-8 $2.81 (**49.7%**) · sonnet-5 $2.85 (50.3%). Contra el KPI
`COST-DOWN §5`: **$/incr −92%** vs baseline $73.89 (VERDE) · **opus-share 49.7% > 35% (ROJO)** — pero de
100% (INC-5/6) → 50%. Matices honestos: (a) la sesión ÚNICA mezcló diseño-S1 (Opus) + ejecución-S2
(Sonnet) — una S2 pura sigue sin medirse sola; (b) el usage de los 2 spawns del `generator` NO está en el
archivo → 49.7% es COTA SUPERIOR del share real. Gap de instrumento detectado: `meta outcome
--transcript` no imprime split por modelo (el KPI no tiene medidor de primera clase) — anotado como H-9
en `docs/reference/COUNCIL-360-AUDIT.md §4`.

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
