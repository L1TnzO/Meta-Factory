<!-- meta:doc sha=b02403845109b0b415361d395a2a7104f61dc5ad updated=2026-07-04T22:27Z -->
# Incremento CONTROL-GROUP

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-04T20:47Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
E1+D-8 fusionados (COUNCIL-360 §6.4.4, ADR-022): correr los DOS brazos del protocolo pre-commiteado
(`specs/foreign-conduit/EXPERIMENT-PROTOCOL.md`) sobre la spec AJENA RealWorld «Conduit» — brazo A =
la fábrica (traducción a `product.yml` + línea 0-modelo + pin), brazo B = agente pelado (Sonnet,
presupuesto acotado, scratch dir) — y arbitrar con la MISMA vara (checklist de capacidades
VERIFICADAS). Decide la historia de VALOR del sistema y falsifica la endogeneidad del benchmark.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Traducción spec→`product.yml` con bitácora de fricción F1–F6 (≈15 min; NO se maquilla lo no-expresable) | ✅ |
| 2 | Brazo A: `meta product new --factory full-stack-kotlin --name conduit` (línea e2e + pin) | ✅ (2 corridas, ambas ROJAS — registradas) |
| 3 | Brazo B: generator pelado en `/tmp/conduit-control`, solo la spec verbatim como input, ≤25 min | ✅ (6.3 min, verificado por nosotros) |
| 4 | Arbitraje con la vara del protocolo + veredicto D-8 en §Evidencia | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. Brazo A: resultado de la línea REGISTRADO tal cual (verde con pin, o rojo con dónde/por qué —
   un rojo es hallazgo D-8, no fracaso a esconder).
2. Brazo B: lo que entregue, verificado por NOSOTROS corriendo sus tests (no narrado por él).
3. §Evidencia: checklist arbitrada + bitácora de fricción + veredicto sobre D-8 (¿el claim de
   generalidad se recorta? ¿cuánto costó traducir?).

## §Bitácora de fricción (Fase 1, medida — la traducción tomó ~15 min, 1 archivo, 7 entidades)
| # | Concepto de la spec | ¿Expresable? | Mapeo / gap declarado |
| --- | --- | --- | --- |
| F1 | «cualquier autenticado escribe; el autor edita lo suyo» (sin roles) | PARCIAL | `roles: [admin, author]` — `admin` es ARTEFACTO del mapeo (FSK exige vocabulario de roles); ownership por fila SÍ fiel (`owned_by: author_id`) |
| F2 | register/login, JWT, password | NO | FSK trae su propio esquema de tokens por rol; los endpoints de auth quedan FUERA — gap declarado |
| F3 | `favoritesCount`/`following` (derivados sobre relaciones) | NO | relación en `Favorite`/`Follow`; el agregado no se computa |
| F4 | `tagList` (campo lista) | NO nativo | normalizado a `Tag`+`ArticleTag` (2 entidades extra) |
| F5 | la spec NO tiene máquina de estados | — | NO se inventa workflow para complacer al benchmark: si `workflow_enforced` falta, es hallazgo D-8 SOBRE EL BENCHMARK |
| F6 | slugs derivados, paginación/filtros, updatedAt | NO | superficie query/derivación fuera del vocabulario CRUD |

## §Evidencia (medido 2026-07-04; artefactos en `specs/foreign-conduit/evidence/`)

### Brazo A — fábrica (2 corridas, 1m00 + 1m15 wall)
1. Corrida FIEL: **ROJA en s7** — `workflow_enforced` no degrada a N/A con cero workflows (F5
   confirmada AL CORRER; la única vía data es apagar s7 entero, perdiendo también la pirámide).
2. Corrida s7:off: **s0–s8 VERDES** (contrato 7 entidades · schema+jooq · compile -Werror ·
   rbac/ownership estáticos · unit) · **s9 ROJA — hallazgo GENERAL nuevo**: el seeder inserta la fila
   sample del target una vez POR CADA ref entrante (Follow: follower_id+followed_id→User) → viola
   unique(username) → server muere al boot (`brazoA-seeder-crash.log`). Topología multi-ref-mismo-
   target que ningún producto propio ejercitó.

### Brazo B — agente pelado (Sonnet, 6.3 min, 68k tok; VERIFICADO por nosotros, no narrado)
`python3 -m unittest discover -s tests` → **9 tests, exit 0** (corrido por el orquestador).
**19/19 endpoints** de la spec (auth por identidad con token firmado, profiles/follow, articles CRUD
con slug-dedup y filtros, comments, favorites, tags, formatos de respuesta/error EXACTOS de la spec).
Gaps declarados en su REPORT: token sin expiry, lock global (no concurrente), validación mínima.

### Arbitraje (la vara del protocolo, misma para ambos)
| Capacidad | A (fábrica) | B (pelado) |
| --- | --- | --- |
| persistencia viva | ✅ s1 (PG real) | ✅ sqlite (tests reales) |
| autorización | PARCIAL (rbac estático ✅; el modelo de la spec es identidad, no roles — F1/F2) | ✅ fiel a la spec (verificado) |
| workflow | N/A (la spec no tiene) | N/A |
| server VIVO enforzando | ❌ (seeder crash) | ✅ (HTTP real 401/403/404/422) |
| fidelidad al FORMATO de la spec | ❌ (contrato CRUD propio) | ✅ exacta |
| re-derivable desde spec | ✅ estructural (la corrida es re-derivable; pin al verde) | ❌ artesanía |
| tasa de escape conocida | ✅ (instrumento E4) | ❌ |

### Veredicto E1+D-8 (honesto, n=1, límites del protocolo aplican)
1. **D-8 CONFIRMADA**: el benchmark sweet-spot mide cobertura de la gramática PROPIA. En spec ajena,
   el agente pelado GANÓ la historia día-1 (19/19 endpoints funcionales en 6 min vs s9-rojo).
2. **El claim de VALOR se recorta y AFILA**: la fábrica no vale por «app más rápida desde cualquier
   spec»; vale por re-derivabilidad probada + gates + tasa de escape EN SU CLASE de producto
   (CRUD+roles+workflow). Fuera de esa clase, hoy pierde — con número y logs, no con relato.
3. **2 gaps GENERALES medidos** para la cola (D-4: nacen como slots): (a) `workflow_enforced` sin
   workflows → N/A honesto, no rojo; (b) seeder dedupe por target con multi-ref. Gatillo: el próximo
   producto real que los pise.
4. La traducción fue BARATA (~15 min) — el costo no explotó; lo que faltó fue COBERTURA (F1–F6).
