<!-- meta:doc sha=a7f567afe9694d1365fc74fc7dad42f946a62809 updated=2026-08-03T22:59Z -->
# Increment V3-EXTRACT-STEP0-FREEZE-WAIVER

> **Governance doc.** Status: **OPEN** (created 2026-08-03T22:57Z). Close it with `v3 increment close`
> (gated: clean tree + active station green). Every code change lives here (ADR-010).
>
> PASO 0 de `work/V3-EXTRACT-DIRECTION-INCREMENT.md` · nodo `N-0132` · autoridad `ADR-023 §3`.

## Goal

Poner en **verde el único rojo del repo** (`codegen_freeze`, rojo en las DOS máquinas desde 2026-07-11)
mediante el mecanismo que el propio gate diseñó para un commit ya en la historia — `WAIVED_COMMITS` —
y, en el mismo acto, **darle diente a esa escotilla**, que hasta hoy era la única superficie sin ley
del módulo.

## La decisión de gobierno (con ojos, no por comodidad)

El hecho, verificado antes de decidir: **`ba05918d2`, 2026-07-13, UN archivo**
(`factories/full-stack-kotlin/codegen/scaffold/data_layer.py`), **UNA línea** — `jsonVal` envolvía
strings en comillas **sin escapar nada**, así que cualquier campo con `"`/`\`/newline emitía **JSON
inválido en cada lectura de lista/detalle de toda entidad de todo producto** de ese codegen.

Se eligió **(a) `WAIVED_COMMITS`** sobre (b) un work-doc FSK abierto, por dos razones escritas:

1. Es una **reparación de corrección** de emisión ya congelada: no evoluciona superficie humana
   (`alcance=superficie`) ni cablea verificación nueva (`alcance=verificacion`). El vocabulario de
   dos valores **no tiene casilla honesta** para esto, y forzar `superficie` exigiría **un ADR
   dedicado para un bug de escapado de comillas**.
2. El commit tiene tres semanas y **ya está en la historia**: no puede hacerse crecer un waiver
   in-tree retroactivo. El docstring autoriza esta vía textualmente — *«never by weakening the gate»*.

## Lo que apareció al usar la escotilla (no estaba en el plan)

Al ir a usarla, la escotilla tenía **dos defectos**, ambos arreglados acá:

| # | defecto | por qué importa |
| --- | --- | --- |
| 1 | **una clave abreviada era un NO-OP SILENCIOSO** — `_audit_history` compara contra el `%H` de 40 chars | la receta literal del doc de dirección (`"ba05918d2": …`) **no habría funcionado**, y el gate habría seguido rojo sin decir por qué. Hoy las claves se **resuelven por git** (`rev-parse`), así que la abreviatura anda |
| 2 | **`WAIVED_COMMITS` no tenía ninguna ley**: cualquier clave con cualquier valor suprimía un rojo | una escotilla de gobierno sin auditoría es un lavadero. **El momento en que una escotilla se usa por primera vez es el momento en que tiene que empezar a ser auditada** |

Ley nueva (`evaluate_waivers`, **pura** → ejercitada por el lado rojo): cada fila prueba **cuatro**
cosas o es rojo — resuelve a un commit real · ese commit **realmente alimentó** `factories/*/codegen/**` ·
es **post-época** (pre-época ya está grandfathered, así que la fila sería decorativa — la misma forma
que el `waiver with NO diff` que el módulo ya castigaba) · y **tiene razón escrita** (≥40 chars).

⚠️ **N-0122 respetado**: en un clon shallow la auditoría histórica es N/A, y ahora el reporte **dice
cuántas filas quedaron SIN auditar** — una fila no-medida no puede leerse como auditada-y-limpia.

## Phases
| Phase | Content | Status |
| --- | --- | --- |
| 1 | `WAIVED_COMMITS` ← `ba05918d203f9…` con razón escrita (acto de gobierno) | done |
| 2 | `evaluate_waivers` — la ley pura de la escotilla + resolución de claves por git | done |
| 3 | lado rojo: 5 escenarios sintéticos nuevos para la escotilla (3 → **8**) | done |
| 4 | aceptación: los dos lados + experimentos negativos sobre el repo real | done |
| 5 | el segundo verificador (CI externo) en verde | done |

## Close criterion (demonstrable, not narrated)

1. `python3 -m v3.verify.checks.codegen_freeze` → **PASS**
   («4 factory/ies …; historical audit: 1 post-epoch commit audited, 1 suppressed by 1 **audited**
   WAIVED_COMMITS row»).
2. `V3_CODEGEN_FREEZE_SABOTAGE=1 …` → **PASS con 8 escenarios** (era 3). El lado rojo **creció**, no
   se volvió N/A — la trampa `N-0125` no se disparó.
3. **Experimentos negativos sobre el repo real** (no sintéticos), monkeypatcheando la tabla:

   | escenario | resultado |
   | --- | --- |
   | tabla real, como quedó commiteada | **GREEN** |
   | clave **ABREVIADA** `ba05918d2` (la literal del doc de dirección) | **GREEN** ← la trampa quedó cerrada |
   | tabla **vacía** (el estado previo) | **RED** ← la supresión es lo que hace el trabajo, no un accidente |
   | clave irresoluble | **RED** |
   | razón real degradada a `"ok"` | **RED** |
   | fila que nombra un commit que nunca tocó `codegen/` | **RED** |

4. El **segundo verificador** (ADR-005), sobre el mismo commit: sin rojos.
