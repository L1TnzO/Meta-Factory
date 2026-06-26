<!-- meta:doc sha=359dba29db80cf38316a43f4db80d195ce1331d3 updated=2026-06-26T13:25Z -->
<!-- meta:doc sha=PENDING updated=2026-06-26T13:24Z -->
# ADR-018 — La columna como proyección de un único source (desacople least-privilege del cp-harness)

| Campo | Valor |
| --- | --- |
| Estado | Aprobado |
| Fecha | 2026-06-26T13:24Z |
| Decide | el ingeniero (2026-06-26, eligió «ADR-016 Fase 2 completa»); ejecuta el orquestador |
| Generaliza | ADR-010 (la ley vive en `seed/`, el hook sólo transporta), ADR-016 (gobierno por nivel, filosofía II — Fase 2), ADR-011/012 (la columna es frontera de seguridad, NO spec-driven), I-12 (toda prohibición de un agent tiene sombra determinista) |
| Referencia | `work/HARNESS-DECOUPLE-INCREMENT.md` (el incremento §1), `reference/GOVERNANCE-LAYERING.md` §4–§6 (catálogo Fase 2), `decisions/017` (re-dirección SOTA: lo difirió a post-grafo), `work/SOTA-REDESIGN-DIRECTION-INCREMENT.md` |

## Contexto

Medición (2026-06-26, fundada en `diff`): la columna de enforcement (cerrojos 1/2/3 + cadencia) existe HOY
en **TRES copias paralelas**:

1. la columna **viva** del meta: `.claude/hooks/*.py`
2. el **template** que siembra fábricas: `template/factory/harness/.claude/hooks/*.py`
3. cada **fábrica** generada: `factories/<f>/.claude/hooks/*.py` (render fiel de (2): subst de `{{slug}}` → 2 líneas)

El drift gordo está entre (1) y (2): **40–63 líneas por cerrojo**. (2) es un **fork a mano** que quedó rancio:
cada cerrojo mejoró en (1) y el template nunca se puso al día. **Nada lo detecta.** Peor: los hooks de
enforcement de delegación que agregó la Fase 2 del norte vigente (`blast_radius`, `verdict_required`,
`gate_guard` — *verificar-no-revisar*) **no existen** en (2) ni (3) → una fábrica **no puede** enforcar el
contrato de delegación. Si un agent de fábrica declara `forbidden_tools`/`blast_radius` (el vocabulario al que
`PWF-VOCAB-HARVEST` le puso diente), la **sombra determinista que I-12 exige no está instalada** → el contrato
es **hueco** a nivel fábrica. El vocabulario tiene diente arriba (meta) y no abajo (fábrica).

Diagnóstico: **tres patologías de una misma raíz** — el cp-harness (M1 instala la columna por `render_tree`
de un template fijo, `stations/m01.yml:12`): **DRIFT** (template rancio), **CAPACIDAD FALTANTE** (delegación
no propagada), **PRIVILEGIO MAL CALIBRADO** (copia en bloque, no proyección por nivel).

**Restricción dura:** la columna es la **frontera de seguridad** y a propósito **NO es spec-driven**
(`stations/m07.yml`: «la COLUMNA la instala M1 y NO es spec-driven»). No se arregla volviéndola DATA — un
spec adversario apagaría un cerrojo.

**Precedente que ya existe:** 3 de 4 cerrojos YA delegan su LÓGICA al seed (`increment_guard` → `seed/lifecycle.py`;
`stop_proof`/`commit_guard` → `seed/verifier.py`); el hook es transporte fino (~50 líneas). ADR-010 ya estableció
«la ley vive en `seed/`, el hook sólo transporta». El problema: ese patrón **nunca se generalizó** — el transporte
y la copia del seed se mantienen a mano y driftean, **sin diente que lo pruebe**.

## Decisión

1. **La columna de cada nivel es una PROYECCIÓN determinista de un único source canónico, no una copia mantenida
   a mano.** Se generaliza ADR-010 a TODA la columna: la lógica vive single-source; el hook in-tree es un
   transporte fino **derivado** de ese source por un transform determinista (parametrización por nivel: `{{slug}}`,
   scope). `template/factory/harness/` deja de ser un fork a mano.

2. **Gate `column_parity` (diente, dogfoodeado).** Un check determinista prueba: columna in-tree de la fábrica
   ≡ proyección(source canónico actual). **Drift = ROJO**, re-derivable (espeja `ci --rederive == pin`). Inyectar
   drift (editar un hook de fábrica) debe tirar el gate a rojo; si no, es prosa.

3. **La proyección es LEAST-PRIVILEGE por nivel.** Emite, por nivel, SÓLO los hooks que ese nivel gobierna —
   ni la columna entera del meta por inercia. Y propaga el enforcement de delegación (`blast_radius`/`verdict_required`)
   a la columna de fábrica **acotado a sus slots** → I-12 (`agent_shadow`) gana **diente a nivel fábrica**: una
   prohibición declarada por un agent de fábrica tiene sombra REAL instalada y cableada. El vocabulario del §4
   (`PWF-VOCAB-HARVEST`) tiene diente **también abajo**.

4. **La frontera de seguridad se mantiene: la proyección NO es spec-driven.** El transform es determinista y fijo
   en el sustrato (no lee DATA de fábrica que pudiera debilitar un cerrojo). Single-source NO se rompe (H1, ADR-016
   §4): la ley sigue en `seed/`, el meta DELEGA, la fábrica HEREDA por **proyección checkeada**, no por copia ciega.

5. **Faseado (orden de dolor).** Esta ADR + §1 (`HARNESS-DECOUPLE`) fija la proyección + el gate + el diente abajo.
   ADR-016 Fase 2 se completa en §2 (lifecycle de fábrica in-tree) · §3 (sellado de docs fábrica/producto) ·
   §4 (close acotado al nivel) — diseño ya en ADR-016 + `GOVERNANCE-LAYERING` §4–§6.

## Consecuencias

- El cp-harness deja de ser un fork rancio: una mejora a un cerrojo se proyecta a todas las fábricas al regenerar,
  y `column_parity` prueba que ninguna driftó.
- La delegación *verificar-no-revisar* (Fase 2) es enforzable **a nivel fábrica**, no sólo meta: una fábrica puede
  delegar a Sonnet con los mismos dientes.
- I-12 deja de ser hueco abajo: el vocabulario de WorkOrder (`forbidden_tools`/`blast_radius`/…) tiene sombra real
  en la columna de fábrica.
- El refactor es seguro **ahora** (no antes): el grafo (Fase 1) + los quality gates (Fase 1–3) lo vuelven medible;
  ADR-017 lo rechazó como arranque («rewrite a ciegas») y lo puso post-grafo. Estamos ahí.

## Rechazado

- **Volver la columna spec-driven** (emitirla por `emit_harness` desde L3 como los agents/commands). Debilitaría
  la frontera de seguridad: un spec adversario podría omitir un cerrojo. La columna se PROYECTA por un transform
  fijo del sustrato, no se declara en DATA.
- **Dejar el template como fork a mano + «acordarse» de sincronizarlo.** Es la disciplina-sin-diente que ya falló
  (40–63 líneas de drift). El valor es el gate, no el recordatorio (lección PWF: vocab → contrato, el valor es el diente).
- **N columnas divergentes por nivel.** Rompería single-source (H1). La proyección parte de UN source; lo que cambia
  por nivel es el SCOPE (qué hooks, parametrización), no la ley.
- **Hacerlo antes del grafo + gates** (ADR-017 ya lo rechazó). Sin la capa de medición es rewrite a ciegas de un motor que funciona.
