<!-- meta:doc sha=fd1671588ddcb1ea8987babd83d3def380225d8e updated=2026-07-03T22:58Z -->
# Incremento IOT-S1-FIELD-VOCAB

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-03T22:19Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

> **HANDOFF AUTOCONTENIDO para una sesión S2 en FRÍO (Sonnet, post-`/clear`).** Lo diseñó una sesión S1 (Opus)
> con más contexto: contrato + gate + blast-radius FIJADOS abajo. Es el **vehículo §5** de `COST-DOWN` — un
> incremento de EJECUCIÓN mecánica representativo → corré la sesión en **Sonnet** (`claude --model sonnet
> --agent orchestrator`) para que `meta outcome` MIDA el KPI `opus-share` sobre un build real. No re-diseñes;
> ejecutá las Fases, aceptá por VEREDICTO, cerrá.

## ★ EMPEZÁ ACÁ (S2 en frío) — qué hacer YA
1. **Reproducí el piso verde** (antes de tocar nada): `PYTHONPATH=src python3 -m metafactory.cli product-run
   --factory iot` (demo `iotgw`) y `--product fleet` → ambos PASS. `./meta check` → 18/18. Ese es el piso.
2. **Abrí el increment ya está ABIERTO** (esta doc). Tocá SÓLO el blast-radius del §2. Al final: `meta increment
   close --factory iot` (gateado: árbol limpio + estación verde).
3. **Delegá el bulk** (el codegen del enum) vía `generate-slot` al `generator` (Sonnet); aceptá por el VEREDICTO
   del §3, no por el diff. La COLUMNA (`src/`, `seed/`) NO se toca — el gate `generality` lo enforza.

## Objetivo
Extender el vocabulario de campos del codegen de iot de **4 tipos base** (`string`·`float64`·`int64`·`bool`) al
tipo **`enum` type-safe en Go** (const-block + validador `Valid<F>` + campo del struct tipado al enum) — el eje R2
(`FSK-S11`) cross-validado en la **2ª cadena de herramientas (Go)**, con diente de dos lados.

## 0. POR QUÉ (R2 en Go — el 2º toolchain + el vehículo §5)
FSK probó "vocabulario de campos arbitrario" (3→8 tipos, enum type-safe) en Kotlin (`FSK-S11`). iot hoy sólo
parametriza `{string, float64, int64, bool}` (`_GO_TYPE`, `scaffold_product.py:29-30`) y `fleet/product.yml`
lo dice explícito: *"la expresividad de campos arbitrarios es R2, diferida"* — una invitación. Portar el eje a
**Go** prueba GENERALIDAD sobre una 2ª cadena (espíritu ADR-014, co-validación en toolchains disjuntos). Además
es el **vehículo §5** de `COST-DOWN`: bulk delegable (codegen + template Go) + gate **rápido·hermético·keyless**
(`go vet`/`go test`, sin LLM, sin gradle, segundos) + slot corto → corrido en Sonnet, mueve `opus-share`.

## 1. Contrato (typed — lo que el codegen GANA)
Un campo `domain.product.message.fields[]` acepta `{ name: <F>, type: enum, values: [<str>, …] }`. El codegen
emite, en el paquete `contract` (`message.go` o hermano), un **enum type-safe de Go**:
```go
type <F> string                                   // NO alias `= string` (perdería la seguridad de tipo)
const (
    <F><SanitizedV0> <F> = "<v0>"
    <F><SanitizedV1> <F> = "<v1>"
    // … un const por value; el identificador se sanea a un ident Go válido (a elección del generator)
)
// Valid<F> reporta si v es un miembro declarado (borde fail-closed, DES-3/DES-8).
func Valid<F>(v <F>) bool { switch v { case <F><SanitizedV0>, <F><SanitizedV1> /*…*/: return true }; return false }
```
- El **miembro del struct** se tipa `<F> <F>` (el enum), NO `string` crudo.
- `_GO_SAMPLE` del enum = el **primer const** (`<F><SanitizedV0>`), un miembro VÁLIDO.
- **Fail-closed** (extiende el diente de `scaffold_product.py:45`): tipo desconocido → exit 1 (ya está); `enum`
  sin `values` (o `values` vacío) → `SystemExit` con mensaje claro.
- **Alcance**: el campo enum del `fleet` es **NO-requerido** → NO tocás la restricción "requerido debe ser
  string" (`:68-70`). Generalizarla (borde de un enum requerido = `!Valid<F>` en vez de `== ""`) es STRETCH §Fase-4.

## 2. Blast radius (allow_globs) + PROHIBIDO
Permitido tocar SÓLO:
- `factories/iot/codegen/scaffold_product.py` — el core (extensión `_GO_TYPE`/`_GO_SAMPLE` + emisión enum + fail-closed).
  Es un archivo EXISTENTE de 665 LOC; el añadido es acotado (~40-60 líneas) → **NO** lo partas ni crees monolito nuevo.
- `factories/iot/products/fleet/product.yml` — adoptar UN campo enum (ver §4 Fase 2).
- `factories/iot/products/fleet/pinned_verdict.json` — re-pin **vía `ci --rederive`**, jamás a mano.
- `factories/iot/docs/work/IOT-S1-FIELD-VOCAB-INCREMENT.md` (esta doc: Fases + §Evidencia) · `factories/iot/docs/{STATE,LOG}.md` (al cierre).

**PROHIBIDO**: `src/**` y `seed/**` (la columna — dientes `generality` + `least_priv`; el vocabulario es DATA en
`codegen/`, sustrato = 0). `factories/iot/stations/**`: EVITALO — embebé el diente negativo en el test generado
`./contract` (tocar una estación COMPARTIDA re-pinea todos los productos).

## 3. El gate (gate_cmd — rápido·hermético; así se ACEPTA el slot)
```
PYTHONPATH=src python3 -m metafactory.cli product-run --factory iot --product fleet   # PASS (go vet ./... && go test ./contract)
PYTHONPATH=src python3 -m metafactory.cli product-run --factory iot                   # demo iotgw: PASS + BYTE-IDÉNTICO (sin enum → path inerte)
PYTHONPATH=src python3 -m metafactory.cli ci --rederive --all-products                # == pin (fleet re-pineado; demo sin cambio)
./meta check                                                                          # 18/18 incl. generality (git diff src/ seed/ = vacío)
```
El slot manifest (`.gen/active_slot.json`, vía `generate-slot`): contract=§1 · allow_globs=`factories/iot/codegen/scaffold_product.py`,
`factories/iot/products/fleet/product.yml` · gate_cmd=las dos primeras líneas de arriba · verdict_path=`.gen/verdict.json`.
Leé el VEREDICTO, no el diff.

## 4. Diente de dos lados (anti-decoración — mirror de la type-safety de FSK-S11)
- **Positivo**: `fleet.Telemetry` gana `{ name: Health, type: enum, values: [ok, degraded, down] }` (NO-requerido).
  `product-run … fleet` → el test generado `./contract` construye `Telemetry{…, Health: HealthOk}` y asevera `ValidHealth(t.Health)`.
- **Negativo (embebido, re-derivable)**: el MISMO test `./contract` asevera `ValidHealth(Health("bogus")) == false`.
  Si el codegen fuera decorativo (alias `type Health = string`, o `Valid` siempre-true) → esa aserción ROJA.
- **La prueba de que no es decorativo**: sabotear la type-safety (ensanchar a `string` crudo / `Valid`→siempre-true)
  DEBE poner s0 (`typed_message_contract`) en ROJO. Registrá el sabotaje→rojo en §Evidencia (como hizo FSK-S11).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Codegen: `_GO_TYPE`/`_GO_SAMPLE` + emisión enum type-safe (`type <F> string` + const-block + `Valid<F>`) en `scaffold_product.py`; fail-closed en enum-sin-values | ✅ |
| 2 | `fleet/product.yml`: adoptar el campo enum `Health` (no-requerido) + embeber el diente de DOS lados en el test generado `./contract` | ✅ |
| 3 | Verde: `product-run fleet` + demo ==pin + `ci --rederive --all-products`==pin + `meta check` 18/18; re-pin fleet | ✅ |
| 4 (STRETCH, opcional) | `type: timestamp`→`time.Time` y/o `required:false`→puntero | ⏭️ no ejecutado (Fases 1-3 ya cerraron el criterio; stretch queda para un incremento futuro si hace falta) |

## Criterio de cierre (demostrable, no narrable)
1. iot codegen soporta `type: enum` con Go type-safe (const members + `Valid<F>` + campo del struct tipado al enum);
   tipo desconocido / enum-sin-values → exit 1 (fail-closed, re-derivable).
2. `fleet` declara un campo enum y `product-run --factory iot --product fleet` PASS (`go vet` + `go test ./contract`
   verde con un miembro válido; la aserción embebida rechaza un no-miembro).
3. Diente de DOS lados probado: sabotear la type-safety pone s0 en ROJO — registrado en §Evidencia.
4. Demo (`iotgw`) BYTE-IDÉNTICO: `product-run --factory iot` sin re-pin; `ci --rederive --all-products` == pin (sólo fleet re-pineado).
5. Anti-overfit: `git diff src/ seed/` VACÍO; `./meta check` verde incl. `generality`.
6. **§5**: correr esta sesión en Sonnet (`--agent orchestrator`) y capturar `meta outcome` (opus-share + $) como el
   vehículo del KPI `opus-share` de `COST-DOWN` §5 (baseline $73.89; target opus-share ≤35%).

## Evidencia (la completa el S2 al cerrar)
Ejecutado vía `generate-slot` → `generator` (Sonnet), 2 spawns (Fase 1 codegen + Fase 2 adopción; el 2º spawn
fue una sesión fresca — este harness no soportó continuar el mismo agent-id por `to`, así que el hand-off fue
un manifest actualizado + contexto autocontenido, no una sesión continuada). Verificado por bloqueo (no por
prosa) en CADA paso:
- `product-run --factory iot --product fleet` PASS (`go vet` + `go test ./contract`) · `product-run --factory iot`
  (demo `iotgw`) PASS, sin cambios.
- **Sabotaje→rojo probado**: el generator forzó `ValidHealth` siempre-true en un harness Go AISLADO (`/tmp`, vía
  Bash, no Write — nunca tocó el repo) → `TestValidHealthRejectsUnknownMember` fue ROJO; revertido → verde. Yo
  (orquestador) confirmé independientemente el diente REAL leyendo el test generado (no la prosa del verdict):
  `factories/iot/products/fleet/build/product/contract/message_test.go` tiene `TestValidHealthAcceptsDeclaredMember`
  (positivo, `HealthOk`) y `TestValidHealthRejectsUnknownMember` (negativo, `ValidHealth(Health("bogus"))==false`) —
  AMBOS presentes.
- `ci --rederive --all-products --factory iot` → **2/2 == pin** (re-corrido por mí independientemente, no solo
  por el verdict). Nota honesta: `proof_sha` = hash de `(station_id, checks (nombre,exit) ordenados)` — NO
  content-hash de los artefactos Go (`seed/verifier.py:compute_proof_sha`) — por diseño (PF-10, doble
  verificador): el pin queda estable mientras el MISMO check nombrado siga saliendo exit 0, aunque el Go
  generado cambie por dentro. `fleet/pinned_verdict.json` NO cambió (byte-idéntico) — esperado, no un bug.
- **Anti-overfit**: `git diff --stat src/ seed/` VACÍO (confirmado por mí). `factories/iot/codegen/scaffold_product.py`
  665→**760 líneas** (+95 netas), dentro del presupuesto multi-archivo (~800). `./meta check` → **18/18** (confirmado
  por mí, post-clear-slot).
- **Gap de diseño S1 encontrado y corregido en vivo (residuo, no re-diseño)**: el manifest original delegó
  `products/fleet/product.yml` sin abrir el incremento de NIVEL PRODUCTO que `increment_guard` exige (ADR-016,
  layering) → 1er spawn devolvió ROJO honesto (no fabricado). Se abrió
  `factories/iot/products/fleet/docs/work/IOT-S1-FIELD-VOCAB-FLEET-INCREMENT.md` + se corrigió un bug real del
  manifest (`acceptance_gate_cmd` sin `--factory iot`, validaba la fábrica default por error) → 2do spawn GREEN,
  confirmado por mí.
- **§5 (opus-share/$ de ESTA sesión S2)**: transcript
  `~/.claude/projects/-home-enzo-University-Integraci-n-APP-Meta-Factory/d14b2cf6-035c-461b-96a8-3f6fdeb95a8d.jsonl`.
  `meta outcome --transcript <ese path>` corre pero NO hay una función `opus_share` en `src/` (grep vacío) — el
  cálculo real (INC-4/5/6) fue una re-derivación AD-HOC de S3 sobre el JSONL crudo con `pricing.PRICING`, no un
  verbo del CLI. Dejo el puntero al transcript para que el S3 (Opus, cierre) haga esa medición — es juicio de
  cierre, no ejecución mecánica; no la fabriqué a mano en esta sesión Sonnet.
