# Incremento FSK-OWNED-REQUIRED-REFS — refs REQUERIDOS no-dueño en la entidad-con-dueño / SEED TRANSITIVO

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **ABIERTO**
> (creado 2026-06-22T03:16Z). Cerralo flippeando este header a CERRADO (el `increment status` lee el header) **o**
> con `meta increment close --factory full-stack-kotlin`. Editar `factories/full-stack-kotlin/**` no-`.md`
> (codegen/spec/stations) exige ESTE incremento abierto — el `increment_guard` elige el lifecycle por la RUTA editada.
>
> **HANDOFF AUTOCONTENIDO para una sesión EN FRÍO (post-`/clear`).** Asumí amnesia total. Lo escribió la sesión que
> cerró FSK-OWNERSHIP-OPTIONAL con MÁS contexto, para que NO re-aprendas lo que ya sabemos.

---

## 0. POR QUÉ este incremento (deferral 4 — el companion que destapó FSK-OWNERSHIP-OPTIONAL)

**FSK está MADURO** (genera→prueba e2e→CRUD del grafo entero bajo control de acceso→UI usable→deploya→self-ref→
dueño nullable/RTD). El trabajo es **product-driven**: construir Snipe-IT trabajando sus deferrals (`products/snipeit/
docs/reference/SNIPEIT-DOMAIN.md §3`), cada uno forzado por un caso REAL. Hermanos YA cerrados: CRUD-mutación,
self-ref (FSK-SELF-REF), **dueño nullable/RTD (FSK-OWNERSHIP-OPTIONAL, el inmediatamente anterior — leé su §Evidencia)**.

**Este = deferral 4 (`SNIPEIT-DOMAIN.md §3 #4`)**: en Snipe-IT real `Asset.model_id` es **REQUERIDO** (un activo
SIEMPRE es de un modelo). Pero hoy el blueprint MIENTE: `model_id` está `required: false` porque **el server vivo
(FSK-S15) NO sabe sembrar un `ref` REQUERIDO no-dueño en la entidad-con-dueño** — `_seed_chain` hace un `raise
SystemExit` explícito ante eso. La fidelidad pide un **SEED TRANSITIVO** (cadena de dependencias multi-nivel:
`Category → AssetModel → Asset.model_id`). Es un gap GENERAL de fábrica, bien acotado, y el companion directo del #3.

**Lección clave del hermano (esperala otra vez):** FSK-OWNERSHIP-OPTIONAL señalaba 2 sitios y **generar de verdad
destapó 4**. FSK-SELF-REF: 1 → 3. **El handoff SUB-ESTIMA los sitios.** Eyeball SIN gradle ANTES de cada corrida.

---

## ★ EMPEZÁ ACÁ (post-clear) — qué hacer YA

**1) Reproducí el verde actual** (el piso: `model_id` aún opcional, RTD ya vivo):
```
cd /home/enzo/University/Integración/APP/Meta_Factory
PYTHONPATH=src python3 -m metafactory.cli product-run --factory full-stack-kotlin --product snipeit
```
⚠️ **`dangerouslyDisableSandbox: true`, FOREGROUND, UN producto a la vez, timeout ≥540000ms** (el sandbox mata
gradle: exit 144). **Mantené el cwd de Bash en la RAÍZ del repo** (un `cd` a un subdir filtra el cwd persistente →
deadlock del hook `stop_proof` al cerrar; si pasa, `cd` de vuelta a la raíz). Debe dar **PASS**. RTM snipeit **24/25**
(único UNSAT = REQ-F-007/s6 LLM keyless). ⚠️⚠️ **s7 PG en 5435 · s9 puertos FIJOS 18593-18595 + PG 5436/5437 · s11
18596** → NUNCA dos corridas en paralelo, NUNCA dejes un `product-run`/`ci` en BACKGROUND al cerrar el turno (el hook
`stop_proof` RE-CORRE la estación activa → colisión de puerto → falso rojo). FOREGROUND, dejá terminar ANTES de cerrar.

**2) Entendé el gap EXACTO** (toda la maquinaria vive en `codegen/scaffold_product.py`):
- **`_seed_chain`** (~L3260): el seeder del server vivo (s9). Hoy:
  ```python
  if f["type"] == "ref":
      raise SystemExit(f"scaffold: AppServer seed: {e['name']} tiene un ref requerido no-dueño "
                       f"{f['name']!r} (FSK-S15 siembra sólo el dueño + campos escalares)")
  ```
  Ese `raise` es la pared. Cuando `Asset.model_id` sea `required: true`, sembrar la fila de Asset (asignada Y RTD)
  pide sembrar PRIMERO un `AssetModel` y wirear `model_id` a su id.
- **El target es de PROFUNDIDAD >1.** `AssetModel` tiene `category_id`→Category **REQUERIDO**. La maquinaria que YA
  siembra ref-targets (FSK-REFS-IN-BODY, `_ref_targets` + `seed_ref_lines` en `_app_server_kt`, ~L3660) usa
  **`_ref_target_seedable`** (~L939) que DEFIERE los targets con su propio ref requerido (`AssetModel` NO es
  "sembrable" hoy por eso). El gap GENERAL: **seed transitivo / topológico** (Category → AssetModel → Asset).
- **El POST del cuerpo.** Con `model_id` requerido, `_input_fields(Asset)` (~L915) lo INCLUYE (ref requerido
  no-dueño) → el `<E>Input` y `_mutation_fns` (~L1051) lo setean `del body` (FSK-REFS-IN-BODY ya hace esto para la
  entidad `with_ref`). El proof (`access_control_check.py`) entonces necesita POSTear un `model_id` VÁLIDO →
  `/seed` debe EXPONER el id del `AssetModel` sembrado para la entidad-con-dueño (hoy `/seed refs` sólo expone los
  refs de la entidad `with_ref`, no los del owned). Mirá `seedJson` / `Seed.refs` en el `_APP_SERVER_SKELETON`.
- **OJO la interacción con FSK-REFS-IN-BODY**: hoy `_live_with_ref` elige `AssetModel` como la entidad servida
  "con-ref" (category_id→Category). Si Asset gana un ref requerido a AssetModel, revisá que las selecciones
  `_live_*` (~L926-987) sigan disjuntas y que el seed no duplique/colisione (AssetModel podría sembrarse dos veces).

**3) EL DISEÑO (resolvelo GENERAL, cero nombres de dominio — `generality` verde es el anti-overfit real):**
- **Un seeder TRANSITIVO general** que, dada una entidad, siembre topológicamente sus dependencias por ref
  REQUERIDO (capturando ids), y luego la entidad con los refs wireados. Reúsalo de forma UNIFORME para owner /
  owned / RTD / with_ref / ref-targets (hoy son 3 caminos casi-iguales: `_seed_chain`, `seed_ref_lines`,
  `_roundtrip_kt`). Cuidá los ciclos (un ref requerido que cierra ciclo → `raise` honesto, sigue diferido — deferral 6).
- **Opt-in / byte-neutro**: un producto SIN refs requeridos no-dueño en su entidad-con-dueño (default `Project`,
  assets `Asset` con `holder_id` el único requerido = el DUEÑO) debe quedar **byte-idéntico** (default/assets sin
  re-derivar). Verificalo con el eyeball (§3) ANTES del gradle.
- **El `/seed` del owned** debe exponer el id del/los AssetModel sembrado(s) para que el proof POSTee la FK válida
  (como hace hoy con `refs` para la entidad with_ref). El diente NEGATIVO ya existe: un ref colgante → 409 fail-closed.

**EL DIENTE de dos lados** (criterio §6.2): con `model_id` requerido, el seed transitivo siembra Category→AssetModel
→Asset; el round-trip cruza la FK viva. **Saboteá**: no siembres el AssetModel (o wirealo a un id inexistente) → la
FK de Asset.model_id falla → **SÓLO** el check afectado rojo (s7 `pyramid_integration` y/o s9 `access_control_live`;
los hermanos de esa estación verdes) → revertí → verde. + el POST con `model_id` colgante → 409 (ya cubierto).

---

## 1. ⚠️ RE-PIN — ¿hace falta?
Si el fix vive DENTRO de los checks existentes (s7 `pyramid_integration` + s9 `access_control_live`/`infra_up`, mismos
nombres+exit), el **`proof_sha` queda INTACTO** → pines byte-idénticos, SIN re-materializar, SIN re-pinear (como
FSK-OWNERSHIP-OPTIONAL y FSK-SELF-REF). **NO agregues check/estación nuevos si podés evitarlo.** `git diff
snipeit/product.yml ≠ 0` es ESPERADO (trabajo de producto); el sustrato + default/assets product.yml DEBEN quedar en
0. **Si default/assets re-derivan ≠ pin**, tu cambio NO fue byte-neutro para ellos → hacelo opt-in (sólo emite la vía
transitiva cuando la entidad-con-dueño tiene un ref requerido no-dueño). `proof_sha = sha256({station,
sorted(check_name, exit)})` — invariante a qué siembra el código.

## 2. Maquinaria a REUTILIZAR (no la reinventes)
- **`_seed_chain`** (~L3260, el `raise` a levantar) · **`_ref_targets`** (~L965) · **`_ref_target_seedable`** (~L939,
  hoy defiere depth>1 — acá lo levantás) · **`_seed_chain(tvar[t], t)` + `seed_ref_lines`** en `_app_server_kt`
  (~L3660, el patrón que YA siembra targets para `with_ref`).
- **`_roundtrip_kt`** (~L1224, s1) y **`_it_repository_kt`** (~L2524, s7) — los OTROS dos seeders que también wirean
  refs; un ref requerido nuevo en Asset puede tocarlos (¡eyeball!).
- **`_input_fields`** (~L915) · **`_input_data_class`** (~L990) · **`_mutation_fns`** (~L1051, ya setea refs del body) ·
  **`access_control_check.py`** (~L3920, el proof; ya tiene el bloque `with-ref` con FK válida + colgante→409).
- **El RTD** (FSK-OWNERSHIP-OPTIONAL): la fila RTD (owner NULL) también necesitará el `model_id` requerido sembrado →
  el seed transitivo aplica a AMBAS filas (asignada + RTD). Mirá `seed_rtd`/`_seed_chain(..., alt=True)` en `_app_server_kt`.

## 3. Lecciones CARAS ya destiladas (NO las re-aprendas)
- **El handoff sub-estima los sitios** (2→4 en ownership, 1→3 en self-ref). Antes de cada gradle lento, **eyeball SIN
  gradle**: un scratch python con `importlib` sobre `codegen/scaffold_product.py` que carga la spec efectiva
  (`bp = yaml(product.yml)`; `sp.build_files(bp)`), y LEÉ AppServer.kt (seedRows/seedJson) + RepositoryIT.kt +
  DbRoundTrip.kt + el migration ANTES de correr. **Y verificá que default/assets quedan byte-idénticos** (emití su
  `build_files` y diffeá el seed). Cazás los huecos sin esperar 2-3 min. (Patrón exacto en el §Evidencia de
  FSK-OWNERSHIP-OPTIONAL — ahí lo usé para confirmar los 4 sitios + byte-neutralidad de default/assets.)
- **`meta verify` re-corre la estación ACTIVA con `build=False`** (no regenera). La activa tras un product-run es
  **s11**. Para un tooth en s7/s9 por la vía canónica: **sabotear el codegen + `product-run`** (rojo en la estación
  afectada, las posteriores no corren) → revertir → `product-run` verde (restaura la activa verde, clave para que
  `stop_proof` no bloquee el cierre del turno).
- **`meta station` corre la META-línea (m00-m08), NO la línea FSK.** Para la línea FSK: `product-run`.
- **`proof_protect` DENIEGA tocar `.proof/` por shell** (incluso leer el log) — pero el **Read tool SÍ** lee los logs
  de `.proof/logs/` (el log es un RESUMEN: nombre de check + exit, no el stdout verboso del proof; el `exit=0` es la
  señal autoritativa). El árbol generado (`products/<p>/build/product/...`) es legible por shell.
- **`dangerouslyDisableSandbox: true`** para gradle/docker (el sandbox los mata: exit 144). cwd SIEMPRE en la raíz.
- **ktlint MaxLineLength = 160** (no 120 — eso es PropertyWrapping, sólo para `val x = Ctor(...)`). Una línea jOOQ
  larga ≤160 está bien (`_jooq_chain` envuelve >160).

## 4. Restricciones DURAS de FSK que SIGUEN vigentes (cada una su incremento)
Refs **polimórficos** (deferral 2: `assigned_to`→User|Location|Asset), **custom-fields dinámicos** (deferral 1, el eje
GRANDE), **verbos de dominio** (checkout/checkin/audit, deferral 11b), **company-scoping** (deferral 8), **ciclos
cross-entidad** (deferral 6: Location/Department.manager_id→User — un seed transitivo que cierra ciclo sigue DIFERIDO).

## 5. Disciplina + dónde van los docs (⚠️ DOS niveles, ADR-016)
- **El fix del codegen** (`scaffold_product.py`) es nivel FÁBRICA → **este incremento** lo cubre (header ABIERTO).
- **La adopción** (`products/snipeit/product.yml`: `Asset.model_id` → `required: true`) es nivel PRODUCTO → abrí
  TAMBIÉN `meta increment open --factory full-stack-kotlin --product snipeit <slug>` ANTES de tocar `product.yml`.
- **Commit = parte del trabajo (ADR-010), NUNCA lo preguntes**; trailers I-10 (`Co-Authored-By: Claude Opus 4.8
  <noreply@anthropic.com>`). Patrón: `feat(fsk): …` (codegen) + `feat(snipeit): …` (product.yml) + `docs(fsk): cerrar
  FSK-OWNED-REQUIRED-REFS (§Evidencia) + abrir <siguiente>`.
- **Probá POR BLOQUEO** (no fakees verde): `product-run --product snipeit` PASS · diente de dos lados vivo (sabotear
  el seed transitivo → SÓLO el check afectado rojo) · `ci --rederive --all-products` == pin (los 3) · `meta check`
  6/6 (`generality` verde) · `git diff src/+seed = 0` · default+assets product.yml = 0.

## 6. Criterio de cierre (demostrable, no narrable)
1. `products/snipeit/product.yml`: `Asset.model_id` → `required: true` y `product-run --product snipeit` **PASS** —
   el server vivo siembra transitivamente (Category→AssetModel→Asset) y la FK `model_id` valida contra la PG viva;
   el POST acepta `model_id` del cuerpo (FK válida de `/seed`→201, colgante→409).
2. **Diente de DOS lados verificado VIVO**: saboteá el seed transitivo (no sembrar el target / id inexistente) →
   confirmá ROJO **sólo** en el check afectado (s7/s9) → revertí → verde.
3. `ci --rederive --all-products` == pin (los 3). `meta check` 6/6 (`generality` verde). `git diff src/metafactory +
   seed = 0`. `git diff` default+assets product.yml = 0. (Si tocaste el set de checks → re-pin justificado.)
4. STATE/LOG (fábrica) + `SNIPEIT-DOMAIN.md §3 #4/§4` actualizados. Abrí el SIGUIENTE con su handoff autocontenido (§7).

## 7. Qué viene DESPUÉS (para que sepas dónde estás parado)
Orden del push Snipe-IT (`products/snipeit/docs/reference/SNIPEIT-DOMAIN.md §4`):
- ~~CRUD-mutación~~ ✅ · ~~self-ref~~ ✅ · ~~ownership opcional/RTD~~ ✅.
- **(este)** refs requeridos no-dueño / seed transitivo (deferral 4).
- **custom-fields dinámicos** (deferral 1) — el eje GRANDE: gramática de campos por modelo (EAV-como-columnas).
  Probablemente el mayor eje de fábrica que Snipe-IT fuerza.
- **operaciones de dominio** (deferral 11b): checkout/checkin/audit como verbos que MUTAN semántica.
- **diferidos DUROS** (red/scope): push a un registry · e2e Playwright · AppServer-en-contenedor con PG · ciclos
  cross-entidad (deferral 6) · checkout polimórfico (deferral 2).
