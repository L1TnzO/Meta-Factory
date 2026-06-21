# Bitácora — Full-Stack Kotlin/TS/PG Factory
> tipo: log · append-only, MÁS NUEVO ARRIBA · inmutable una vez escrito (esquema ADR-021).

## 2026-06-21T13:44Z — FSK-S16 ✅: el server vivo MUTA columnas (no sólo da el veredicto)
- **Cierra el 1er hueco de §5 que Snipe-IT expuso**: hasta FSK-S15 el server vivo DECIDÍA el acceso
  (403/200/201) pero no mutaba columnas end-to-end. Ahora **POST inserta** una fila tipada jOOQ (dueño =
  principal del actor) y devuelve el id · **PUT /{id} actualiza** la 1ª columna `string` no-unique no-dueño ·
  **DELETE /{id} borra** · + ruta viva **GET /{id}**. Todo DESPUÉS del veredicto OK (RBAC + ownership), con
  `modifyVerdict` (ex `statusForPut`) reusado para PUT y DELETE. Mutaciones tipadas en `Repository.kt`.
- **El diente pasó de VEREDICTO a ROUND-TRIP e2e** (`access_control_check.py`): POST→count+1 · PUT→GET /{id}
  ve el valor nuevo · DELETE→count vuelve + 404; los dientes de acceso siguen (prohibido→403 sin mutar,
  no-dueño→403 sin mutar). **Diente de DOS lados VIVO**: UPDATE saboteado (matchea 0 filas) → s9 rojo.
- **Probado por bloqueo**: `product-run snipeit` PASS · RTM **19/20** (REQ-F-015 `crud_mutacion_runtime`
  SATISFIED; único UNSAT = s6 LLM keyless) · `ci --rederive --all-products` **3/3 == pin** · `meta check`
  `generality` verde. **Anti-overfit**: `git diff src/metafactory/ + seed/` = 0 · `git diff product.yml` = 0
  (el cambio vive en `codegen/scaffold_product.py` + `factory.spec.yml`).
- **Gaps GENERALES destapados y arreglados acá** (el handoff no los había previsto): columna UNIQUE → valor
  único en runtime (nanoTime; el seed ya ocupaba el sample) · `import java.time.LocalDate` (date requerido) al
  FINAL por el layout de ktlint_official · `@file:Suppress("TooManyFunctions")` en AppServer (9→15 fns).
- **Sigue**: body-parsing JSON + PATCH · CRUD de entidades sin dueño · ownership opcional/RTD · self-ref ·
  custom-fields · frontend React + deploy + e2e. Autoridad: `docs/work/FSK-CRUD-MUTACION-REAL-INCREMENT.md`.

## nacimiento — generada por el Meta-Factory
- La fábrica full-stack-kotlin se construyó corriendo M0–M8 sobre su factory-spec. El sustrato no se
  escribió a mano: ascendió del template del Meta-Factory (los 13 invariantes), verificado por gate.
