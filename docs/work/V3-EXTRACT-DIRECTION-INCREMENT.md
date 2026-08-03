<!-- meta:doc sha=0ab1ee86d5a075f0a76ed2ff766d18bbb1254421 updated=2026-08-03T22:53Z -->
# Dirección — V3-EXTRACT: sacar `v3/` de este repo y usarlo en otro lado

> **Doc de dirección** (no es un incremento abierto; cada PASO de abajo se abre con
> `meta increment open <SLUG>` en el nivel que corresponda). Creado 2026-08-03T22:5xZ tras
> **medir** la extracción, no estimarla.
>
> Autoridad: `ADR-031`/`ADR-032` · `spec/11-build-plan.md` · `ADR-016` (gobierno por nivel) ·
> `ADR-005` (los dos verificadores). Nodos: ver §6.

## 0. La conclusión, en una línea

**No hay nada roto bloqueando la salida.** Hay **un rojo con dueño** (nivel FSK), **seis fixtures que
mudar**, y **una decisión de gobierno sin tomar** —«la migración terminó»— que si se toma mal borra
once dientes en silencio. La ingeniería está hecha; falta el acto de gobierno y su instrumento.

---

## 1. Lo que YA está medido — no lo repitas, verifícalo si dudás

Ensayo hecho el 2026-08-03. Reproducible tal cual:

```bash
R="/home/enzo/University/Integración/APP/Meta_Factory"
cd /tmp && rm -rf v3-extract && mkdir v3-extract && cd v3-extract
cp -r "$R/v3" . && git init -q . && git add -A && git -c user.email=x@y -c user.name=x commit -qm x
# 130 módulos, 130 importan: CERO imports a v2. El gate import_boundary ya pagó esa deuda.
```

| medida | resultado |
| --- | --- |
| módulos v3 que importan en un repo vacío | **130 / 130** |
| gates totales hoy | **42** |
| `meta check` local (árbol final de INC-12) | 40 verdes · 1 rojo · 1 N/A |
| CI externo sobre el mismo commit (`30859533087`) | 31 verdes · **1 rojo** · 4 N/A |
| el rojo, en las DOS máquinas | `codegen_freeze` — `N-0084` |

**El paquete mínimo, medido** (con esto: **13 gates verdes · 0 rojos · 4 N/A** en un repo ajeno sin
historia de v2, y `meta attach --factory dummy --driver repl` levanta y contesta):

```
v3/  seed/  tools/  docs/spec/  tests/fixtures/  benchmarks/  factories/  meta
```

- `seed/` — es la cadena de confianza; los hooks la cargan **por path**, no por import.
- `docs/spec/` — **no es documentación, es código**: el álgebra del plan se EJECUTA desde
  `15-plan-and-memory.md §5` (y el kernel desde `§14`). Sacarlo rompe `plan_tree` y `leaf_context`.
- `tools/` — `spec_conformance.py` es el extractor de esos bloques.

### 1.1 Los 42 gates, clasificados por si viajan (medido, no opinado)

Re-derivable con:
```bash
python3 - <<'PY'
import sys; sys.path.insert(0,'.')
from pathlib import Path
from v3.verify.suite import build_registry
for g in build_registry(Path('.')).gates():
    mod = g.argv[-1]; p = Path(mod.replace('.','/')+'.py')
    src = p.read_text() if p.is_file() else ''
    print(('C-oraculo' if ('_show' in src or 'oracle_ref' in src) else
           'B-fixture' if (g.witness and g.witness.kind != 'sabotage_env') else 'A-libre'), g.name)
PY
```

| clase | n | gates |
| --- | --- | --- |
| **A · viajan gratis** | **25** | `attach_authority` `attach_parity` `compaction` `compile` `dial` `docs` `escape_threshold` `generality` `isolation` `iteration` `kinds` `leaf_context` `ledger` `pbt` `plan` `plan_tree` `projection` `rederive` `roles` `run_log` `slot_footprint` `state_fidelity` `state_snapshot` `suite` `telemetry_liveness` |
| **B · necesitan un fixture fuera de `v3/`** | **6** | `benchmark` `deferred` `design_eval` `evidence_liveness` `quality` `security` |
| **C · leen v2 en el commit oráculo → mueren al extraer** | **11** | `cli_parity` `codegen_freeze` `column_law_parity` `deletion_manifest` `economy_census` `eval_floor_parity` `eval_gate_parity` `live_run_parity` `migration_census` `session_memory_parity` `verb_census` |

**La clase C no es deuda: es el ANDAMIO de la migración.** Existe para probar «v3 == v2». Extraer no
la rompe: **le saca el sujeto**. La pregunta que contesta ya está contestada.

---

## 2. PASO 0 — el waiver de FSK (bloquea el resto; nivel `full-stack-kotlin`)

Es el único rojo, en las dos máquinas, desde **2026-07-11**. Hasta que no esté verde, no tiene sentido
extraer: te llevarías un rojo a la casa nueva.

**El hecho exacto**, ya verificado:

```bash
python3 -m v3.verify.checks.codegen_freeze
# full-stack-kotlin: commit ba05918d2 fed codegen/ with NO open waiver in its own tree
git show --stat ba05918d2   # 2026-07-13, fix(FSK-CODEGEN): escape quotes/backslashes/newlines in jsonVal
git show --name-only --format="" ba05918d2 | grep codegen/
# factories/full-stack-kotlin/codegen/scaffold/data_layer.py   ← UN archivo, UN commit
```

Es un **arreglo de corrección** (jsonVal no escapaba comillas/backslashes/newlines → JSON inválido en
cada lectura de lista/detalle de toda entidad de todo producto). No evoluciona la superficie humana ni
cablea verificación nueva. Por eso hay dos caminos y **hay que elegir con los ojos, no por comodidad**:

| camino | cómo | costo |
| --- | --- | --- |
| **(a) `WAIVED_COMMITS`** — el mecanismo que el propio gate diseñó para un commit **ya en la historia** | `v3/verify/checks/codegen_freeze.py:64`, hoy `{}`: agregar `"ba05918d2": "<razón escrita>"` | es un **acto de gobierno con ojos y razón escrita**, y el docstring lo autoriza textualmente: «never by weakening the gate» |
| **(b) waiver en un work-doc FSK abierto** | `meta increment open FSK-CODEGEN-FREEZE-WAIVER --factory full-stack-kotlin` y en el doc: `Codegen-freeze-waiver: alcance=verificacion · motivo: … · cita: ADR-023` | ⚠️ si lo clasificás `alcance=superficie` **exige un ADR dedicado** (CLAUDE.md, ADR-023 §3) |

**Recomendación**: **(a)**. El commit tiene 3 semanas de antigüedad y ya está en la historia; abrir un
incremento hoy para amparar retroactivamente un commit de julio es la forma incómoda, y `WAIVED_COMMITS`
existe exactamente para esto. Pero es **tu** decisión de nivel: escribí la razón, no la excusa.

**Aceptación del PASO 0** (las dos, no una):
```bash
python3 -m v3.verify.checks.codegen_freeze                       # PASS
V3_CODEGEN_FREEZE_SABOTAGE=1 python3 -m v3.verify.checks.codegen_freeze   # también PASS (lado rojo vivo)
```
⚠️ **Si el lado rojo se vuelve N/A o deja de morder al agregar el waiver, PARÁ**: es exactamente
`N-0125` (un lado rojo muere cuando lo que planta se vuelve universalmente cierto, y nadie avisa).

Después: `git push` y **leer el CI externo** (`gh run list --limit 1`). Debe dar **32 verdes · 0 rojos ·
4 N/A**. Ese número es el hito real: *el segundo verificador en verde por primera vez desde 2026-07-09*.

---

## 3. PASO 1 — el manifiesto del paquete, como DATO con diente (nivel meta)

`meta increment open V3-EXTRACT-MANIFEST`

1. `v3/extract_manifest.py` (NUEVO): la lista de §1 como **DATO**, no prosa —
   `PACKAGE: tuple[tuple[str, str], ...]` = (path, por qué viaja). Una fila por directorio, y la razón
   es obligatoria: `seed/` viaja porque los hooks la cargan por path; `docs/spec/` porque el álgebra se
   ejecuta desde el documento.
2. `v3/verify/checks/extract_package.py` (NUEVO) — el gate. **Verde**: cada path del manifiesto existe
   y está trackeado por git; y —lo que importa— **ningún módulo de clase A referencia un path FUERA del
   manifiesto** (barrido con `ast`/regex sobre literales de string, la técnica de `verb_census`).
3. Lado rojo `V3_EXTRACT_PACKAGE_SABOTAGE=1`, ≥3 plantados:
   (1) un módulo de clase A referencia un path fuera del manifiesto;
   (2) una fila del manifiesto apunta a algo que no existe;
   (3) una fila sin razón escrita.
4. Registrar en `v3/verify/suite.py` con `witness=Witness("sabotage_env", "V3_EXTRACT_PACKAGE_SABOTAGE")`.

**Aceptación**: el gate verde + su rojo mordiendo + `meta check` sin rojos nuevos.

---

## 4. PASO 2 — clase B: los 6 fixtures viajan CON su gate (nivel meta)

`meta increment open V3-EXTRACT-FIXTURES`

Hoy 6 gates dependen de archivos dispersos. El ensayo lo demostró de la forma correcta: la suite
**se negó a arrancar** (`RegistrationRefused: quality: red-side fixture … is not in the tree`) en vez
de correr sin dientes. Ese comportamiento **no se toca**: es la ley de INC-4 y es lo que hace que la
extracción sea honesta.

Trabajo: para cada uno de `benchmark · deferred · design_eval · evidence_liveness · quality · security`,
dejar su fixture bajo un path que el manifiesto del PASO 1 declare. Mover, no copiar; `git mv`.

⚠️ `evidence_liveness` tiene un problema APARTE y anterior (`N-0102`): resuelve referencias contra
`../Agent_Systems_Factory/`, **un repo hermano que el gate no declara ni valida**, así que su color lo
fija el ENTORNO y no el commit. Al extraer, eso se vuelve un rojo garantizado. **Decidilo acá**: o el
gate declara y valida esa dependencia, o se retira con razón escrita. No lo arrastres.

**Aceptación**: el ensayo de §1 con SOLO el manifiesto → los 31 gates de clase A+B registran y corren.

---

## 5. PASO 3 — clase C: el CENSO DE RETIRO (nivel meta) — **el paso peligroso**

`meta increment open V3-EXTRACT-RETIREMENT`

Retirar 11 gates de paridad es, mecánicamente, la jugada más peligrosa que sabe hacer este repo:
**quitar once dientes de una**. La regla que lo hace honesto es la de P7 de INC-12, un nivel más arriba:

> **Retirar está permitido. Retirar sin decidir, no. Y un retiro sin PRUEBA de que el sujeto
> desapareció es una remoción de diente disfrazada de limpieza.**

1. `v3/verify/retirement.py` (NUEVO): `RETIREMENT: dict[str, tuple[str, str]]` = gate →
   (`"retire"|"keep"`, razón). Los 11 de clase C, uno por uno, con su razón escrita.
2. **La prueba, no la afirmación.** Para cada `retire`, el censo debe demostrar que **el sujeto ya no
   existe**: que ningún path que el gate compara sigue en el árbol, o que su oráculo es inalcanzable
   por construcción. `deletion_manifest` ya sabe hacer exactamente esta contabilidad — reusala, no
   escribas una segunda ley.
3. **Un gate de clase C que todavía tiene sujeto NO se retira.** Ojo con `codegen_freeze`: lee el
   oráculo, **pero su sujeto (`factories/*/codegen/`) viaja con el paquete**. Ése es `keep`, y hay que
   re-basarlo para que no dependa de `git show <oráculo>`.
4. Lado rojo `V3_RETIREMENT_SABOTAGE=1`, ≥3 plantados: (1) un gate marcado `retire` cuyo sujeto **sigue
   en el árbol**; (2) una fila sin razón; (3) un gate de clase C **sin fila** (no decidido).

**Aceptación**: el censo verde; el conteo de `meta check` baja de 42 a `42 − retirados` **y el número
de retirados coincide exactamente con las filas `retire`**. Un gate que desaparece sin fila es rojo.

---

## 6. PASO 4 — la extracción y su aceptación (nivel meta)

`meta increment open V3-EXTRACT-CUTOVER`

1. Repo nuevo con el manifiesto del PASO 1. `v3/oracle_ref.json` **se retira o se re-apunta**: en el
   repo nuevo no hay commit de v2.
2. **Aceptación, y las dos mitades se declaran por separado** (la lección de `§11.6` de INC-11 — nunca
   fundir dos actores en un número):
   - **máquina de desarrollo**: `meta check` sin rojos, y `rederive` == pin **sobre los 10 targets**
     (`dummy` · `iot`+`fleet` · `full-stack-kotlin`+`assets`+`helpdesk`+`snipeit` ·
     `agent-systems-factory` · `full-stack`+`tasks`);
   - **la otra máquina** (ADR-005): lo que su toolchain permita, **imprimiendo lo que NO corrió**.
3. `meta attach --factory dummy --driver repl` levanta y contesta en el repo nuevo (ya verificado en el
   ensayo — que no se pierda al mudar).

---

## 7. Trampas, cada una con su nodo — leelas ANTES de empezar

| # | trampa | por qué |
| --- | --- | --- |
| `N-0122` | **`actions/checkout` clona SHALLOW.** En el runner los módulos que leen el oráculo mueren por *falta de historia*, no por diseño | un verde ahí puede significar **«no corrió»**, no «ya no hace falta». Medí en un clon PROFUNDO antes de concluir que un gate de clase C está listo para retirarse |
| `N-0125` | **un lado rojo muere cuando lo que planta se vuelve universalmente cierto, y el gate sigue pasando** | después de CADA paso, corré los lados rojos, no sólo los verdes |
| `N-0124` | **dos re-derivaciones concurrentes producen un rojo FALSO** | `meta check` ya incluye `rederive` sobre los 10 targets: **no lances `ci --rederive` en paralelo** |
| `N-0128` | `meta check` corre **~35 min sin imprimir NADA** hasta el final | no lo mates con `timeout` corto: perdés hasta los gates que ya pasaron. Usá `> archivo` y esperá |
| `N-0130` | la ley del slot rechaza `.gen/active_slot.json` | si delegás alguno de estos pasos, el generador **no puede** ampliarse el radio: ampliáselo vos en el manifiesto |
| — | **no fabriques `v3/attach_facts.json`** | el driver `model` está construido y **sin correr**; correrlo cuesta plata y es decisión del ingeniero |

---

## 8. Orden, y por qué ése

**PASO 0 → 1 → 2 → 3 → 4.** El 0 primero porque un repo cuyo segundo verificador está verde vale más
que cualquier feature, y porque no se muda un rojo a una casa nueva. El 3 (retiro) **después** del 1 y
el 2, porque hasta que el paquete no esté declarado no se puede probar que un sujeto desapareció: sin
manifiesto, «no está» y «no lo copié» son indistinguibles.

**Lo que NO es parte de esto**: los 7 verbos a portar (`graph{,/build,/query,/repomap}`, `outcome`,
`billing`, `metrics` — `HUMAN_VERB_DISPOSITION` en `v3/verify/verb_census.py`). Son su propio
incremento y van **después** de la extracción, no antes.
