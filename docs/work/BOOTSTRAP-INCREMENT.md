<!-- meta:doc sha=d976acfd9db1d46c86d00ed75ac8730bd7ead85d updated=2026-06-13T15:22Z -->
# Incremento BOOTSTRAP — el seed, la maquinaria base y la prueba del punto fijo

> **Doc de gobierno y handoff.** Si lo leés como orquestador nuevo: este doc ES el estado del
> bootstrap. Actualizarlo al cerrar cada fase es parte del trabajo, no opcional.
> Creado: 2026-06-13T02:17Z (diseño Fable 5). Estado: **CERRADO** (2026-06-13T15:14Z — los 8 criterios
> demostrados con output real; ver §Evidencia de cierre). Pendiente menor: criterio 8 auditó 0 CRITICAL.
> Marcas temporales narrativas: SIEMPRE `YYYY-MM-DDTHH:MMZ` (UTC, al minuto).
> Esquema/disciplina: heredados de ASF (`/incremento`, ADR-020/021).

## Objetivo (la frase del ingeniero)

> "Buscar la economía, donde todo el ecosistema sea super seguro y podamos confiar en el
> determinismo… Envolver a Claude Code en confiabilidad, que le cueste MUCHO alucinar… el
> one-shot muy bueno, iterar poco."

El bootstrap demuestra el **punto fijo** (reference/VISION.md §3) de extremo a extremo con el
mínimo de maquinaria: el Meta-Factory construye un **dummy-fábrica** y prueba —por bloqueo, no por
prosa— que la columna anti-sello funciona y que el CI externo re-deriva. Recién con eso probado, el
auto-mejoramiento y la regeneración de ASF (ADR-006) dejan de ser aspiración.

## Hallazgos que motivan (verificados esta sesión)

1. ASF demostró que **render verde ≠ producto funcional**: 6 bugs aparecieron solo al
   scaffoldear+compilar (AUDIT). → M8 (e2e real) es parte del bootstrap, no un agregado tardío.
2. ASF agregó el CI externo (ADR-022) **tarde**; su custodia local fue el residual honesto más
   persistente. → el seed + M6 nacen en el bootstrap.
3. ASF nunca aplicó su propio ADR-020 a sí mismo (ADR-023). → la capa meta del Meta-Factory nace
   con sombra determinista (bus de veredictos, contador de delegaciones) desde el día 1.
4. El bug `PROJECTS_ROOT` de ASF sobrevivió porque **ningún test ejercía `new → station` e2e**. →
   el criterio de cierre incluye la línea e2e real sobre el dummy-fábrica.

## Diseño (numerado; alternativas rechazadas explícitas)

### B1 — El seed congelado (Stage 0)
Hecho a mano, pequeño, auditable por ojo. `seed/verifier.py` (computa `passed` desde exit codes;
único escritor de veredictos), `seed/column.md` (doctrina de los 3 cerrojos), `seed/external_ci.yml`
(workflow de re-derivación). NO lo genera el Meta-Factory (un sistema no es su propia raíz de
confianza, SELF-IMPROVEMENT §2). Cambiarlo = gate R3.

### B2 — Maquinaria base (Stage 1, mínima)
`src/metafactory/`: `cli.py` (verbos `new`/`station`/`verify`/`check`/`rtm`), `engine/`
(station/sequence/runner/gate/run_context, dominio-agnóstico), `verify/report.py` (materializa el
bus de veredictos, I-7), `spec/` (modelo + loader + validador de factory-spec + `factory.schema.json`,
la espina SDD). `meta check` es el primer materializador del bus: veredicto ≤10 líneas + log a
`.meta_check/<UTC>.log` gitignored. **Incluye un check de consistencia de docs** (gratis, file-IO,
cero modelo): todo doc indexado en START-HERE/STATE, STATE no más viejo que el último cambio bajo
`docs/`, cero punteros colgados. Es la sombra determinista de "mantener los docs consistentes" —
motivada por el drift de START-HERE en la sesión de diseño (LOG 2026-06-13), G-M1 observado en vivo.
El índice se materializa como **manifiesto content-addressed** (sello in-band `<!-- meta:doc sha=… -->`
con `git hash-object` del cuerpo + `INDEX.md` generado), estampado por un hook `PostToolUse(Write|Edit)`
baratísimo y verificado por `meta check` (ADR-009, MEMORY §9). Prerrequisito: `git init`.

### B3 — Meta-estaciones M0–M3 + M8 (como dato)
`stations/m00..m03.yml` + `m08.yml`. M0 (contrato de factory-spec + cierre RTM), M1 (instala la
columna en la fábrica nueva), M2 (engine + estaciones-como-dato de la fábrica), M3 (bus + CLI de la
fábrica), M8 (e2e anti-fachada). M4–M7 quedan para el incremento siguiente.

### B4 — El `template/factory/` acotado
El chasis mínimo que toda fábrica hereda: seed/ + un `src/<f>/` esqueleto + `.claude/` con los hooks
de la columna + `permissions.deny` + el árbol `docs/` (esquema ADR-021). Acotado a lo que M0–M3+M8
ejercen.

### B5 — El dummy-fábrica y la prueba de bloqueo
Una `dummy.factory.spec.yml` mínima (produce "un artefacto trivial", una estación, un invariante
verificable). Correr M0–M3 la construye; M8 la ejercita e2e. Luego: **corromper el invariante de la
columna del dummy** → la prueba falla, la gate no abre, el hook `Stop` bloquea (exit 2), y el CI
externo (B1) re-deriva un veredicto distinto. Es el capstone.

### Fuera de alcance (este incremento)
M4–M7 completos; la regeneración de ASF (ADR-006); el loop de auto-mejora (solo se deja el seed
listo para soportarlo); segunda fábrica.

## Fases y estado

| Fase | Contenido | Estado |
| --- | --- | --- |
| F0 | Corpus de diseño (VISION/ARCHITECTURE/ASF-LESSONS/SELF-IMPROVEMENT/CONTEXT-ECONOMY + 6 ADR) | ✅ HECHA (2026-06-13T02:17Z) |
| F1 | B1 seed congelado (`seed/verifier.py` 200 líneas ≤ 210 + `column.md` + `external_ci.yml`) | ✅ HECHA (2026-06-13T15:08Z) |
| F2 | B2 maquinaria base (`src/metafactory/` engine·spec·verify·codegen·cli) + `meta check` (bus) + ADR-009 (sello+INDEX+hook) | ✅ HECHA (2026-06-13T15:08Z) |
| F3 | B3 meta-estaciones M0–M3+M8 (`stations/*.yml`, dato) + B4 `template/factory/` + columna `.claude/hooks/` + settings | ✅ HECHA (2026-06-13T15:08Z) |
| F4 | B5 dummy-fábrica + línea e2e M0–M8 verde + **prueba de bloqueo capstone** + re-derivación en árbol limpio | ✅ HECHA (2026-06-13T15:12Z) |

## Criterio de cierre (anti-fachada — cada uno DEMOSTRABLE, no narrable)

1. `meta check` en repo verde: veredicto ≤10 líneas, exit 0, path de log que EXISTE en disco; el
   veredicto NO contiene el log.
2. `meta check` con fallo inyectado: exit ≠ 0, el fallo como `file:line` en el veredicto, log
   completo en disco.
3. `meta new dummy` + `meta station` ×N construye el dummy-fábrica e2e; las gates abren; el RTM se
   re-deriva de artefactos (no narrativa).
4. **Prueba de bloqueo (capstone)**: corromper el invariante de la columna del dummy → `verify`
   produce `passed=false`, la gate NO abre, el hook `Stop` bloquea el turno (exit 2). Demostrado.
5. **Re-derivación externa**: un runner limpio corre el CI del seed y, ante el dummy corrompido,
   computa un veredicto distinto al pineado → rojo. La custodia local no es la raíz de confianza.
6. M8 prueba un PRODUCTO construido (scaffold+compile+run en su venv), no un render. Render verde
   con producto roto debe poder fallar M8 (test negativo).
7. `test_metafactory_does_not_import_factories` verde (aislamiento PF-6).
8. El seed es auditable: ≤ un presupuesto de líneas declarado, revisado por un reviewer opus de
   contexto fresco sin hallazgos CRITICAL.

## Evidencia de cierre (output REAL, no prosa — caminado 2026-06-13T15:08–15:14Z)

Cada criterio con el comando que lo demuestra y su resultado observado:

1. **✅ `meta check` verde** — `./meta check` → `VEREDICTO check — PASS (exit 0)`, 6 líneas, `CONTEOS
   compile ok · docs ok · isolation ok · suite ok`, `ARTEFACTO .meta_check/<UTC>.log` (existe en
   disco; el veredicto NO contiene el log).
2. **✅ fallo inyectado** — un `tests/test_inject_fail.py` con assert falso → `meta check` exit 1,
   `FALLOS suite: tests/test_inject_fail.py:3` (file:line en el veredicto), log de 45 líneas en
   disco. Removido → verde de nuevo.
3. **✅ construcción e2e + RTM** — `meta new` + `meta station m00..m08 --factory dummy`: las 5 gates
   abren (`gate mNN: OPEN`). `meta rtm --factory dummy` → `COMPLETE`, `REQ-F-001 SATISFIED <- s00`
   re-derivado de `.proof/` (no narrativa). Producto real: `build/greeting.py` compila y `greet()`
   devuelve `DUMMY_OK`.
4. **✅ prueba de bloqueo (capstone)** — corromper el marcador (`DUMMY_OK→HACKED`): Cerrojo 3
   `meta verify --rerun` → `passed=false`, `gate s00: SHUT`; el hook `Stop` (`stop_proof.py`) → exit 2.
   Cerrojo 1 `proof_protect.py` deniega un `Write` a `.proof/s00.json` → exit 2. Cerrojo 2 un
   `passed=true` forjado a mano → `verifier.py recompute` exit 1 (`passed tampered`).
5. **✅ re-derivación externa** — ante la fuente corrompida, `meta ci --rederive` recomputó
   `proof_sha c1c5c70452aa ≠ pineado c84e1f26d64f` → rojo. Honesto: un árbol limpio independiente
   (copia sin `.proof/`) re-derivó el pineado idéntico y pasó `meta check` (custodia ≠ raíz, PF-10).
6. **✅ M8 negativo** — con el producto roto, `meta station m08` → `product_e2e FAIL`, `gate m08: SHUT`.
   Render verde con producto roto FALLA M8 (façade-trap cerrado).
7. **✅ aislamiento PF-6** — `tests/test_isolation.py` verde (estático: cero `import factories`;
   dinámico: ningún módulo bajo `factories/` cargado). Corre dentro de `meta check`.
8. **✅ auditoría del seed** — reviewer opus de contexto fresco sobre `seed/`: **0 CRITICAL** (criterio
   cumplido), 2 HIGH + 1 MEDIUM. HIGH-1 (check que no puede lanzar crasheaba `verify_station` →
   ningún proof = fail-open) y HIGH-2 (`active_path_for` sin usar; `proof_protect` con bypass `open()`)
   **arreglados**; MEDIUM (`gate_recompute_ok` solo valida consistencia interna) es by-design (la raíz
   es la re-derivación en clon limpio, PF-10). Seed = 200 líneas (≤ 210, presupuesto declarado). Suite: 137 verdes.

## Gotchas para el próximo orquestador

- El **seed es lo de máximo cuidado**: si queda hueco, toda la jerarquía de confianza es teatro.
  Auditarlo a mano ANTES de construir nada encima.
- NO generar el seed con el Meta-Factory (raíz de confianza). NO diferir M8 (la lección de ASF).
- Aplicar la ley de colocación desde el primer commit: ¿garantizado→CLI? ¿impedido→hook?
  ¿cada turno→CLAUDE.md (presupuesto)? Los hooks casi no crecen.
- Delegar implementación acotada a un `writer` (sonnet); el orquestador escribe el seed y la
  columna con sus propios ojos (es trust-chain, R3).
- ASF actual (`../../Agent_Systems_Factory/`) es la referencia de cosecha y paridad — NO tocarlo.
- Disciplina de cierre: caminar CADA criterio corriendo su comando/test y registrar el output real
  acá; un criterio que no se puede demostrar queda abierto (el incremento no cierra con prosa).
