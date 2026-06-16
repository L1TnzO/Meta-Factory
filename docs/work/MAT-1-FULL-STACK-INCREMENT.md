<!-- meta:doc sha=de20af543a6ce3dabd540d1e25acac701bc67e02 updated=2026-06-16T22:25Z -->
# Incremento MAT-1-FULL-STACK

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-16T22:24Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo

La **Full-Stack-Factory mínima viva** (ROADMAP F2 / MATURITY-PLAN MAT-1): el **2º dominio radicalmente
distinto** (TypeScript), generado 100% desde su spec por un codegen LOCAL (en la fábrica, ADR-012), que
emite un producto web real mínimo — **contrato tipado + backend + frontend + DB relacional** — y lo PRUEBA
en su propio toolchain (DES-8): `tsc --strict` (DES-6), tests con `node:test`, y una **DB `node:sqlite`
viva detrás de un socket-Unix** vía `infra_up` (DES-9/E1). Es el instrumento de co-validación que vuelve
ejercitable el gate de MAT-0: con un 2º lenguaje (ts ⟂ python) los mecanismos de sustrato compartidos
(`product_env`/`generate`/`infra_up`) **promueven a `general`** y `generality_parity` sigue verde —
**legítimamente** ahora.

## Diseño (el porqué)

- **Hermético y re-derivable** (la lección de dummy/E1, no la de network-pesado): el único `npm install` es
  `typescript` (el type-checker no tiene análogo stdlib; ASF paga lo mismo con `pip install`). Todo lo demás
  es **Node stdlib**: `node --experimental-strip-types` (corre TS), `node:test` (runner), `node:sqlite` (DB
  relacional sin servidor). La DB "levanta" como un server `node:sqlite` sobre socket-Unix (el análogo TS
  EXACTO del servicio E1 de dummy: sin docker, sin puertos, race-free).
- **El sustrato no se toca** (ADR-014): toda la tech TS vive en `factories/full-stack/` (codegen + spec).
  `git diff src/metafactory/` por este dominio = **0 líneas** (la medición dura, §5). La maquinaria
  (engine + columna + product_env + infra_up + generate + materialize_line) ya existe — la fábrica la hereda.
- **El type-check ES el gate** (análogo del `mypy --strict` de ASF): `contract.ts` es importado por
  `handler.ts` (backend) y `ui.ts` (frontend); un drift del contrato rompe `tsc` en ambos. Esa es la prueba
  por bloqueo de DES-6.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `specs/full-stack.factory.spec.yml` real mínima (L0–L5: caps DES-6/4/8/9, blueprint `domain.product`, línea s0 generate+tsc / s1 backend-test / s2 DB-viva, machinery harness+infra) — M0 valida 0 problemas | ⏳ |
| 2 | `factories/full-stack/codegen/scaffold_product.py` (determinista, lee el blueprint, emite el producto TS) + registrar (`meta new`) | ⏳ |
| 3 | Línea viva e2e: `product-run` PASS · M0–M8 verde · pin · `ci --rederive` == pineado (re-corre `npm install`+tsc+node:test+DB) | ⏳ |
| 4 | Promover `product_env`/`generate`/`infra_up` a `general` en `parity.yml` (ts ⟂ python) → `generality_parity` **verde legítimo**; sustrato intacto (`git diff src/ = 0`) | ⏳ |
| 5 | Bloqueo VIVO (3 dientes sobre el producto emitido): drift de contrato → `tsc` rojo (s0) · test roto → s1 rojo · DB caída → `infra_up` rojo | ⏳ |
| 6 | Docs (STATE/ROADMAP/MATURITY-PLAN + evidencia) + cierre; dummy+ASF intactos (principio #4) | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. Un producto full-stack GENERADO compila (`tsc --noEmit --strict`), pasa sus tests y **levanta su DB**
   relacional viva — todo por `product_env` + `infra_up`, en el toolchain del producto (DES-8). `product-run`
   PASS · M0–M8 verde · `ci --rederive` == pineado.
2. **`generality_parity` verde con `product_env`/`generate`/`infra_up` ya `general`** (probados en ts ⟂
   python): el lockstep de MAT-0 ejercido. `git diff src/metafactory/` por full-stack = **0 líneas**.
3. **Bloqueo vivo**: drift de contrato → `tsc` rojo · DB caída → `infra_up` rojo (no decorativo).
4. dummy + ASF intactos (`ci` 5/5 · 6/6); congelado `@ b1fcb1f` intocado; `meta check` verde.
