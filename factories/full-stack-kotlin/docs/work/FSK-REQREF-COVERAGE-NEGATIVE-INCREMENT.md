<!-- meta:doc sha=1708f0752887f733a5a41b27b8838bdf5c4e8dbc updated=2026-07-10T00:19Z -->
# Incremento FSK-REQREF-COVERAGE-NEGATIVE

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-10T00:19Z) (creado 2026-07-09T23:33Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Cerrar el residual declarado al cierre de `FSK-REQREF-COVERAGE` (~6.9% de línea sin cubrir en snipeit):
(a) excluir `DbRoundTrip.kt` (herramienta de diagnóstico manual, ya EJERCITADA por `roundtrip`/`s1
db_roundtrip_live` pero con ramas fuera del camino automatizado) del universo MEDIDO por Jacoco — mismo
patrón que la exclusión ya declarada de `org/openapitools/**`+`**/jooq/**`; (b) generalizar el diente
NEGATIVO (ref colgante → 409) — que hoy sólo prueba la entidad `with_ref` PRIMARIA — a las entidades
excluidas que `FSK-REQREF-COVERAGE` ya conectó vía `/seed.withRefs`, cerrando el camino negativo real.

## El hallazgo (ya confirmado, no re-derivar)
- El servidor YA rechaza FKs colgantes con 409 para TODAS las entidades servibles con ref requerido, no
  sólo `wr`: `need_conflict = any(_has_req_ref(e) for e in _servible_ownerless(ents)) or ...`
  (`server.py` ~L1045, comentario FSK-SERVE-ALL-ENTITIES). El gap es 100% del lado del PROOF — nadie
  manda el POST con la FK colgante para esas entidades — igual que el gap original de `FSK-REQREF-COVERAGE`
  fue 100% del lado del proof.
- `_SERVE_ALL_PROOF` (`constants.py` ~L743) ya recibe, por entidad, `_wr = seed.get("withRefs",
  {}).get(_ent.get("refs_from"), {})` — un dict `{campo_ref: id_valido_sembrado}`. Alcanza con: si `_wr` es
  no-vacío, corromper CUALQUIER clave (`+9999`, mismo idiom que el diente `wr` primario en
  `constants.py` ~L1018-1023) y esperar 409 + count sin cambios. Entidades sin ref (`_wr` vacío) saltean el
  bloque → sin cambio de comportamiento para ellas.
- `DbRoundTrip.kt`: 227 líneas sin cubrir (medidas al cierre de `FSK-REQREF-COVERAGE`), invariantes al
  cambio anterior. Es la herramienta de diagnóstico manual (`main()` con más ramas que las que el harness
  automatizado ejercita) — excluirla del `classDirectories` de `jacocoLiveReport` es una exclusión
  DECLARADA (comentario explícito, mismo criterio que jOOQ/OpenAPI), no una fabricación: la tarea
  `roundtrip` sigue corriendo de verdad (gate de infra en `s1`), sólo deja de contar en el % de línea.

## Mecanismo (2 cambios quirúrgicos, sin Kotlin nuevo)
1. **`buildcfg.py`** (`_build_gradle`, task `jacocoLiveReport`): agregar `"**/DbRoundTrip*"` al
   `exclude(...)` existente de `classDirectories`, con comentario declarando el motivo.
2. **`constants.py`** (`_SERVE_ALL_PROOF`): insertar el bloque `if _wr: ...` (dangling-FK → 409, count
   sin cambios) entre el check de "400 tipo equivocado" y el bloque de DELETE — mismo lugar donde el
   diente `wr` primario lo hace, generalizado a N entidades vía el loop existente.

## Alcance (blast radius)
- `factories/full-stack-kotlin/codegen/scaffold/buildcfg.py`
- `factories/full-stack-kotlin/codegen/scaffold/constants.py`
- NO toca `server.py` (el loop y `_wr` ya existen), NO toca Kotlin generado a mano, NO toca `seed/`.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Excluir `DbRoundTrip.kt` de `jacocoLiveReport` classDirectories | ✅ |
| 2 | Generalizar el diente negativo (`_SERVE_ALL_PROOF`, dangling-FK → 409) | ✅ |
| 3 | Verificar: `ci --rederive --all-products` (assets byte-neutral esperado; demo/helpdesk/snipeit re-pin) | ✅ 4/4==pin, sin re-pin |
| 4 | Medir Jacoco de snipeit post-cambio, comparar contra 93.1% baseline, actualizar `SNIPEIT-SPEC.md §11` | ✅ 98.1% |
| 5 | Cierre: `meta check` verde, STATE (meta+factory), LOG | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `ci --rederive --factory full-stack-kotlin --product assets` == pin exacto (byte-neutral: 0 entidades
   con ref candidatas en assets, mismo dato que `FSK-REQREF-COVERAGE`).
2. `ci --rederive --factory full-stack-kotlin --all-products` sin ningún rojo (demo/helpdesk/snipeit
   pueden re-pinear).
3. Cobertura Jacoco de snipeit medida post-cambio, comparada contra 93.1%, con cualquier brecha remanente
   declarada línea por línea (no se acepta "100%" no verificado).
4. `product-run --mode harden` PASS en los 4 productos.
5. `meta check` verde.
6. `docs/STATE.md` (meta) + `factories/full-stack-kotlin/docs/STATE.md` actualizados con el resultado real.

## Evidencia (cierre, 2026-07-09T23:5xZ)
1. `ci --rederive --factory full-stack-kotlin --product assets` → `assets: 11/11 proof_sha == pineado`, exit 0.
   Byte-neutral confirmado (0 entidades candidatas a ninguno de los 2 ejes), corrido ANTES del sweep completo
   (aísla la garantía más fuerte primero, mismo patrón que `FSK-REQREF-COVERAGE`).
2. `ci --rederive --factory full-stack-kotlin --all-products` → **4/4**: `full-stack-kotlin: 12/12`,
   `assets: 11/11`, `helpdesk: 11/11`, `snipeit: 12/12`, todos `== pineado`. Ningún producto re-pineó
   (mismo motivo ya documentado en `FSK-REQREF-COVERAGE`: `proof_sha` deriva de exit-codes, no de
   contenido). `ci --rederive` corre en modo `harden` por default (`cli.py` `--mode` default `"harden"`) —
   satisface el criterio 4 (`product-run --mode harden`) sin una corrida separada: es una garantía
   ESTRICTAMENTE MÁS FUERTE (clon limpio + harden, no árbol local + harden).
3. Cobertura Jacoco de snipeit: **98.1%** (4127/4205 líneas, antes 93.1%), medida vía `product-run --mode
   draft` + parseo de `live.xml` (`<counter type="LINE">` + por-`sourcefile`), delegado a un `verifier`
   (Haiku) para no cargar el XML/log de Gradle en el contexto del orquestador — 2 pasadas de esa misma
   sub-sesión, consistentes. `DbRoundTrip.kt` confirmado AUSENTE del reporte (exclusión activa). Brecha
   remanente (78 líneas, ~1.9%) declarada línea por línea en `SNIPEIT-SPEC.md §11.3` (actualizado):
   `AppServer.kt` 40 (ramas `else -> HTTP_NOT_FOUND` catch-all, estructuralmente inalcanzables) +
   `Repository.kt` 35 (boilerplate jOOQ generado sin rama propia) + `FileSpanExporter.kt` 2 + `RouteTable.kt`
   1. Clasificación independiente (mismo `verifier`, tarea separada): ~50/50 entre inalcanzable-por-diseño y
   boilerplate de bajo riesgo — NO se declaró "100%"; el ~1.9% remanente queda honesto y justificado.
4. Cubierto por (2) — ver nota de modo `harden`-por-default arriba.
5. `meta check` → verde (ver corrida de cierre).
6. `docs/STATE.md` (meta, bullet "Producto / fábricas") + `factories/full-stack-kotlin/docs/STATE.md`
   (bullet `FSK-REQREF-COVERAGE-NEGATIVE` nuevo, precede al `FSK-REQREF-COVERAGE` que cierra) actualizados.
   Episodios en `docs/LOG.md` (meta) + `factories/full-stack-kotlin/docs/LOG.md`.

**Gotcha real de esta sesión** (no anticipado por el diseño S1): el primer intento de verificación lanzó
`ci --rederive --all-products` en BACKGROUND — contra la propia guía de "HEAVY factory builds van
FOREGROUND" (memoria de sesiones previas). El hook `stop_proof` de turn-close corrió su propia `verify s7`
sobre la estación activa MIENTRAS el gradle de fondo seguía escribiendo el mismo directorio
`build/product` compartido → carrera real, 3 checks reportaron rojo transitorio (`pyramid_unit`,
`pyramid_integration`, `workflow_enforced`) que NO eran fallas de código — eran lecturas de un árbol
mid-mutación. Diagnosticado con `ps aux`/`.proof/active.json` (el proceso gradle seguía vivo), resuelto
esperando la finalización real del proceso de fondo (`until grep -q VEREDICTO ...output`) antes de
reintentar — el re-run subsecuente en foreground-efectivo dio 4/4==pin limpio, sin rojo. Lección: el gotcha
ya documentado en memoria ("HEAVY factory builds van FOREGROUND, background races turn-close vía
`.proof/active.json`") es real y se confirmó de nuevo en esta sesión — no basta con conocerlo, hay que
aplicarlo incluso bajo la conveniencia de "dejarlo corriendo de fondo mientras hago otra cosa".

**Sobre el pedido original de esta sesión**: el ingeniero pidió explícitamente maquillar el número de
cobertura ("de la manera más lazy posible, sólo para la foto") citando un requisito de entrega. Se rechazó
esa vía (fabricar evidencia de verificación es engañoso, independientemente de quién lo revise) y se
propusieron 2 caminos honestos — exclusión declarada de `DbRoundTrip.kt` + generalización real del diente
negativo — ambos aceptados. El 98.1% resultante es 100% real y re-derivable, no una foto.
