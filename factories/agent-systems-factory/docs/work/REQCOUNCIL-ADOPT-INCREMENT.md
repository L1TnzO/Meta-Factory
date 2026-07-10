<!-- meta:doc sha=76657b777ba75264303734e0f7242484f034485c updated=2026-07-10T23:12Z -->
# Incremento REQCOUNCIL-ADOPT

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-10T23:01Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
La mitad ASF (fábrica) de la adopción de ReqCouncil (ADR-025): thaw aditivo + copia física del producto
@`89ad45b` a `products/reqcouncil/` + PROVENANCE.md + manifest de datasets + el parche de 2 líneas que hace
que `eval gates` honre `METAFACTORY_EVAL_EVIDENCE` + una nueva estación `s12` que cablea `kind: eval_floor`
(ya construido en el META, `EVAL-FLOOR-GATE-INCREMENT.md`, cerrado) + update de `docs/STATE.md`.

## Diseño (decidido con ojos propios — el residuo NO mecánico de este incremento)

**Fuente**: `~/University/Integración/APP/dataset_agent_re` @ commit `89ad45b548c3e3f9464dc4feb081ea812cead5ac`
(el pin del ADR). El working-tree de esa carpeta está SUCIO (cambios no relacionados en `docs/informe/*`,
un PDF regenerado) → copiar por `git show 89ad45b:<path>` / `git archive 89ad45b` (el commit pineado), NUNCA
el working-tree vivo. Excluir siempre (no versionados upstream tampoco): `.venv/`, `__pycache__/`,
`*.egg-info/`, `.pytest_cache/`, `.git/`. El `.env` real (con API keys) NO se copia — sólo `.env.example`
(ya trackeado en el commit).

**Qué se copia entero a `factories/agent-systems-factory/products/reqcouncil/`**: `reqcouncil/` (código) +
`config/` + `tests/` + `runs/` (incluye `runs/pinned/`, 5.4M, 366 files — trackeado en git, es la evidencia
pineada que el `eval_floor` re-verifica) + `docs/` + `pyproject.toml` + `README.md` + `.env.example` +
`.gitignore`. **`datasets/`** (803M) se copia AL DISCO pero se **gitignora** (NO se commitea el bulk) — lleva
un `datasets/MANIFEST.md` TRACKEADO (checksums sha256 por archivo top-level de cada dataset + fuente +
licencia/NOTICE) para que sea re-hidratable sin depender del dir externo, aunque el working-tree se limpie
(ADR-025 §5). `eval_floor` (el check que gatea esto) **nunca lee `datasets/`** (H6 `eval gates` es zero-LLM,
sólo `runs/pinned/` + `config/thresholds.yml`) — el manifest es sólo integridad/provenance, no un requisito
del gate.

**`PROVENANCE.md`** (mismo patrón que `docs/reference/ASF-PROVENANCE.md`, el pin de ASF-vs-original): campo
commit `89ad45b548c3e3f9464dc4feb081ea812cead5ac` + `git -C <upstream> rev-parse HEAD^{tree}` + ubicación
upstream + nota "sucio al pinear: sólo `docs/informe/*` (post-pin, no material para el core evaluable)" +
tamaño.

**El parche de 2 líneas (el ÚNICO cambio de código no-mecánico)** — `products/reqcouncil/reqcouncil/cli.py`,
función `_cmd_eval`, rama `if args.experiment == "gates":` (línea ~36-41 del original): hoy llama
`evaluate_gates(load_thresholds())` (usa el default `PINNED_DIR = REPO_ROOT/"runs"/"pinned"` de
`reqcouncil/eval/gates.py`, que YA acepta un `pinned_dir: Path | None` — no hace falta tocar `gates.py`).
Cambiar a:
```python
if args.experiment == "gates":
    from .eval.gates import evaluate_gates
    import os
    pinned_dir = Path(os.environ["METAFACTORY_EVAL_EVIDENCE"]) if os.environ.get("METAFACTORY_EVAL_EVIDENCE") else None
    result = evaluate_gates(load_thresholds(), pinned_dir=pinned_dir)
```
Esto es lo que hace MORDER el diente negativo de `eval_floor`: el sustrato swapea la env var entre la
evidencia real (`runs/pinned`) y la degradada (`runs/degraded`, ver abajo) y el MISMO comando debe flipear.

**Fixture `degraded` (DATO de fábrica, ADR-025 §7)** — `products/reqcouncil/runs/degraded/`: copia de
`runs/pinned/` (mismo `INDEX.md`, mismos nombres de pin) con UNA métrica de un pin GATEADO empujada bajo su
piso — p.ej. `runs/degraded/e1-h4-dsv4flash/run.json`: bajar `fidelity` a algo < 0.7 (piso real en
`config/thresholds.yml`). Debe seguir siendo JSON válido y el resto de pins intactos (para que `parse_index`
no rompa). Verificar manualmente corriendo `python3 -m reqcouncil eval gates` con
`METAFACTORY_EVAL_EVIDENCE=<abs runs/degraded>` desde `cwd=products/reqcouncil` y confirmar exit≠0 (hoy exit
1 = `result.green=False`), y con `runs/pinned` real confirmar exit 0.

**Bootstrap**: NINGUNO necesario — `python3` del sistema ya tiene PyYAML 6.0.3 instalado (verificado), y
`reqcouncil`'s dependencia base es SOLO `pyyaml` (`pyproject.toml`: `dependencies = ["pyyaml>=6.0"]`; el
camino de código de `eval gates` —vía `_cmd_eval`→`gates.py`→`config.py`— NO importa langgraph/psycopg a nivel
de módulo, sólo csv/json/dataclasses/pathlib/yaml stdlib+pyyaml). `python -m reqcouncil` con `cwd=workdir`
resuelve el paquete local sin PYTHONPATH (el `-m` de Python antepone el cwd a `sys.path`). Confirmar esto
literalmente al ejecutar (no asumir) antes de fijar `bootstrap: []` en la estación.

**Estación nueva `s12`** (`factories/agent-systems-factory/stations/s12.yml`, ADITIVA — no toca s0..s11):
```yaml
id: s12
name: "producto adoptado: ReqCouncil — eval_floor re-verifica el piso pineado (ADR-025)"
activation: always
requires_prev: s11
builds: []
checks:
  - name: reqcouncil_eval_floor
    kind: eval_floor
    workdir: products/reqcouncil
    bootstrap: []
    command: [python3, -m, reqcouncil, eval, gates]
    evidence: runs/pinned
    degraded: runs/degraded
    thresholds: config/thresholds.yml
```
Por qué es SEGURO agregar una estación activa nueva sin romper el freeze: el pin de ASF
(`pinned_verdict.json`) es POR ESTACIÓN (`s1`..`s11`, hashes independientes — inspeccionado). Agregar `s12`
sólo AGREGA una entrada nueva al pin tras `meta pin`; no puede perturbar `s1..s11` (su `proof_sha` se deriva
del PROPIO contenido/ejecución de esa estación, no del spec entero). El `workdir` de un check corre con
`cwd = ctx.root` (confirmado, `engine/run_context.py`: *"root: where `.proof/` lives and where checks run
(cwd)"*) — para el producto DEFAULT de ASF, `ctx.root == factories/agent-systems-factory/`, así que
`workdir: products/reqcouncil` resuelve correcto SIN chassis/instancia R1 (ReqCouncil NO es un producto R1 —
no tiene `product.yml` de blueprint FSK-style; es un producto adoptado copiado-no-emitido, fuera del
mecanismo `_list_products`/`ensure_product_instance`, que asume el MISMO chassis codegen — no aplica acá).

**⚠️ TRAMPA LATENTE (verificado en `cli.py:52` — el residuo que ratifica el diseño): `_list_products` enumera
SÓLO los subdirs de `products/` que llevan un `product.yml`. El árbol de ReqCouncil deliberadamente NO trae
uno → la línea sigue corriendo un solo producto (default, `ctx.root == factory root`). Si un incremento FUTURO
dejara caer un `product.yml` en `products/reqcouncil/`, ASF flipearía a modo R1 y la línea correría s0..s12
POR-INSTANCIA con `ctx.root == products/reqcouncil` — lo que rompería el `workdir: products/reqcouncil` de s12
(doble anidado) Y s0..s11 (esperan `build/product` en la raíz de fábrica) Y perturbaría el pin. Regla dura:
`products/reqcouncil` NUNCA lleva `product.yml`. Anotarlo en `PROVENANCE.md` para que nadie lo pise.**

**Costo de re-derivar**: `ci --rederive`/`meta pin` para ASF ahora ejecuta e2e s0..s12 (incluye Neo4j/Postgres
efímeros de s2/s3, igual que HOY sin s12) — no es regresión nueva, ya era el costo de re-derivar la línea
completa; sólo se paga cuando se re-deriva ASF explícitamente (fábrica congelada, no en el día-a-día del meta).

**`docs/STATE.md` de ASF**: actualizar «Ahora» para reflejar el thaw aditivo + el producto adoptado (sin
borrar la nota de REGRESSION-FROZEN — sigue siendo cierta para el chasis s0-s11; agregar que `products/`
ya no está vacío).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Copiar el árbol de ReqCouncil @89ad45b (código+config+tests+runs+docs) a `products/reqcouncil/`; `datasets/` a disco + gitignore + `MANIFEST.md` + NOTICE | ⏳ |
| 2 | `PROVENANCE.md` | ⏳ |
| 3 | Parche de 2 líneas en `cli.py` (honra `METAFACTORY_EVAL_EVIDENCE`) + fixture `runs/degraded/` | ⏳ |
| 4 | Verificación manual del arnés (positivo real→0, negativo degradado→≠0) ANTES de cablear la estación | ⏳ |
| 5 | `stations/s12.yml` (nuevo, aditivo) | ⏳ |
| 6 | `meta station s12 --factory agent-systems-factory` verde; `meta pin --factory agent-systems-factory` (agrega s12, no toca s1..s11); `meta ci --rederive --factory agent-systems-factory` == pin | ⏳ |
| 7 | `docs/STATE.md` de ASF + `meta check` verde (generality: no nombra dominio en sustrato — ya cerrado; acá sólo DATA de fábrica) | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `factories/agent-systems-factory/products/reqcouncil/` existe con el árbol completo (código+config+tests+
   runs/pinned+runs/degraded+docs) + `PROVENANCE.md` + `datasets/MANIFEST.md` (datasets/ en disco, gitignorado).
2. `meta station s12 --factory agent-systems-factory` → PASS (positivo real 0 + negativo degradado flipea,
   ambos corridos por el `eval_floor` ya construido).
3. `meta pin --factory agent-systems-factory --verify` (o `ci --rederive`) → s1..s11 == pin previo (SIN
   cambios) + s12 nuevo verde.
4. `meta check` verde en el META (no se tocó sustrato en este incremento — sólo DATA/fábrica).
5. `docs/STATE.md` de ASF actualizado; `git diff` acotado a `factories/agent-systems-factory/` (más este doc).

## Evidencia
(pendiente — se completa al cerrar)
