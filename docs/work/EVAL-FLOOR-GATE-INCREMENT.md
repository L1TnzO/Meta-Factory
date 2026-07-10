<!-- meta:doc sha=eed675ed45155b1422285ddbc1540d94a1fb6bb1 updated=2026-07-10T22:48Z -->
# Incremento EVAL-FLOOR-GATE

> **Doc de gobierno.** Estado: **CERRADO** (2026-07-10T22:48Z) (creado 2026-07-10T22:38Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Dar al sustrato el **kind de check `eval_floor`** (ADR-025 §3): la GENERALIZACIÓN de `design_floor` — un producto
adoptado declara su **perfil de verificación externo** como DATO (comando hermético auto-gateante + evidencia
pineada + piso) y la línea de fábrica lo corre OPT-IN, 0-modelo, **verificando-no-re-derivando** (ADR-023 §4).
Es la mitad META (TRUST-CHAIN) de la adopción de ReqCouncil; la copia física + la data del producto + el arnés
que honra el env son la mitad ASF (incremento aparte, S2).

## Por qué kind de sustrato (no script de fábrica) — la LEY, con ojos propios
`design_floor` se quedó como probe de FÁBRICA porque su diente es TECH-específico (Chromium). El diente de
`eval_floor` — *swapear el env de evidencia, correr un comando auto-gateante declarado, exigir que la evidencia
pineada exista* — es **domain- Y tech-agnóstico**: PURO MECANISMO, reusable por cualquier fábrica que adopte un
producto evaluable. Esa generalidad es lo que lo hace COLUMNA, exactamente como `eval_gate` es kind de sustrato
(no script) por ser mecanismo general. El conocimiento de dominio (qué comando, qué evidencia, qué es una
corrida MAL) queda como DATO de fábrica (ADR-012). Protegido por `generality` (no nombra dominio).

## Diseño — contrato tipado (DATO que el producto declara)
- `workdir` (default `.`): dir del producto, relativo a la raíz de fábrica.
- `command` (req, argv): el comando hermético AUTO-GATEANTE de re-verificación (exit 0 = piso se sostiene).
  Honra `METAFACTORY_EVAL_EVIDENCE` para elegir contra qué evidencia gatea (la palanca del negativo).
- `evidence` (req, path): la evidencia pineada REAL (`runs/pinned/`). Debe EXISTIR y ser no-vacía → un producto
  opt-in SIN evidencia pineada = ROJO (§7 lado A).
- `degraded` (req, path): evidencia deliberadamente MAL (DATO de fábrica, como el `degraded` de `eval_gate`) —
  la palanca del diente negativo.
- `thresholds` (req, path): el archivo de PISO (`config/thresholds.yml`). Se asserta PRESENTE, **no se lee** — el
  sustrato no conoce las métricas (verificar-no-re-derivar; el piso lo re-verifica el comando del producto).
- `bootstrap` (opt, argv): prepara el toolchain del producto una vez, env SCRUBBEADO (DES-8, como
  `eval_gate`/`product_env`) — el comando corre en el entorno del PRODUCTO, no pide prestado el de la fábrica.

**Veredicto = el EXIT CODE del comando** (el producto se auto-gatea; el sustrato NUNCA re-implementa la métrica).

## Diente (two-sided, substrate-owned — refleja `eval_gate`)
1. **Evidencia**: `evidence`/`degraded`/`thresholds` deben existir; `evidence` no-vacía. Falta → exit 2.
2. **POSITIVO**: corré `command` con `METAFACTORY_EVAL_EVIDENCE`=REAL → debe salir 0 (el piso se sostiene).
3. **NEGATIVO** (no-decorativo): el MISMO `command`, sólo cambia `METAFACTORY_EVAL_EVIDENCE`→DEGRADADO → debe
   FLIPEAR (exit ≠ 0). Si la evidencia MAL pasa igual, el arnés ignora su input → prosa, no medición → ROJO.
El sustrato controla el negativo (owns el swap del env) → la fábrica no puede meter un arnés más débil sólo para
el negativo: lo único que cambia entre las dos corridas es la evidencia que el comando lee.

`eval_floor` vs `eval_gate` (kinds hermanos, dos SHAPES de verificación):
- `eval_gate` (MAT-4): el sustrato GRADÚA — el scorer imprime `SCORE:m=f`, el sustrato compara vs `thresholds`.
- `eval_floor` (ADR-025): el arnés del producto se AUTO-GATEA — exit code = veredicto; el sustrato corre + flipea
  la evidencia. Adoptar un producto entero evaluable = re-verificar su arnés VERBATIM, no re-expresarlo.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `verify/checks/eval_floor.py` (la ley two-sided) + wiring en `registry.py` (`resolve_check` + `KINDS`) — columna, ojos propios | ✅ |
| 2 | test dogfood two-sided (`tests/test_eval_floor.py`): pasa el arnés discriminante · detecta el decorativo · evidencia faltante = 2 | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `meta check` verde (incluye `kinds`: `eval_floor` en `registry.KINDS`; `generality`: no nombra dominio).
2. El test dogfood pasa: comando discriminante+evidencia real → 0 · comando decorativo (ignora el env) → 1 ·
   evidencia faltante → 2.
3. `git diff` acotado a `src/metafactory/verify/checks/eval_floor.py` + `registry.py` + el test + este doc
   (NO toca fábricas: la adopción física de ReqCouncil es el incremento ASF, S2).

## Evidencia
- `meta check` **20/20 verde** (`kinds` ok = `eval_floor` en `registry.KINDS`; `generality`/`quality`/`suite` ok).
- `tests/test_eval_floor.py` **8/8**: discriminante+real→0 · decorativo→1 · real bajo piso→1 · pin
  faltante/vacío→2 · thresholds faltante→2 · sin `command`→2 · unlaunchable→127.
- `git diff` acotado: `eval_floor.py` (nuevo) + `registry.py` (+kind) + el test (nuevo) + este doc + STATE/INDEX
  (gobierno). **Cero archivos de fábrica** — la adopción física de ReqCouncil es el incremento ASF (S2).
- Commit feat: `9f8c978`.
