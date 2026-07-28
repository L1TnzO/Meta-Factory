<!-- meta:doc sha=8dacf412a281973d26a1cc9e2afee7bb1aeffefe updated=2026-07-28T17:35Z -->
# Incremento V3-INC1-KERNEL-PORT

> **Doc de gobierno.** Status: **OPEN** (creado 2026-07-28T17:30Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
>
> Autoridad: `ADR-031` (Approved) · spec `docs/spec/14-kernel-reference.md` (el kernel normativo) +
> `11-build-plan.md §2` (el criterio de paridad). Nodos `N-0013` (padre) + `N-0067`. Nivel: meta.

## Objetivo

Que el kernel de v3 reproduzca los pins que existían **antes** que él. Es la afirmación falsable más
barata de toda la reconstrucción: si no la pasa, nada de lo que se construya encima vale la pena.

## Cómo se portó — desde la SPEC, no desde v2

`v3/kernel/proof.py` está transcrito de `docs/spec/14-kernel-reference.md`, que lleva el álgebra como
bloque ejecutable y ya está contrastado por `tools/spec_conformance.py` contra los mismos vectores.
Eso hace dos cosas a la vez: v3 sostiene la misma ley sin importar una línea de v2 (la frontera de
ADR-031), y la fuente de la ley es el documento — que es lo que §12 afirma y aquí se ejerce.

Separado por responsabilidad: `proof.py` calcula la identidad de UNA estación; `pin.py` compara una
línea entera contra lo commiteado.

## El oráculo NO era el que la spec decía

§11.2 mandaba recomputar sobre «los `.proof/*.json` **ya commiteados** de las 5 fábricas».
**`.proof/` está gitignored**: `git ls-files | grep .proof/` devuelve **cero**. Ese oráculo no existe.

Lo que sí está commiteado —y existe justamente porque alguien chocó con esto antes— es
`docs/spec/fixtures/proof-sha-vectors.json`: 84 vectores de `origin·station·checks·proof_sha`, cada
uno anclado a un pin. La cadena hermética es entonces de **dos eslabones independientes**:

> recomputar el sha desde los checks → debe igualar al vector → el vector debe igualar al pin commiteado.

Comprobar sólo el primero sería auto-referencial: el vector confirmándose a sí mismo. §11.2 queda
corregida en el propio documento.

## Un agujero en mi propio gate, que el número delató

La primera versión cargaba únicamente los pins de FÁBRICA e imprimía **40/40** — verde, y falso. Los
84 vectores tienen dos clases de origen: línea de fábrica (`iot`) y línea de PRODUCTO (`iot/fleet`),
cada una con su pin commiteado. Los 44 vectores de producto caían en un contador de «sin anclar» que
el camino verde ni siquiera imprimía, así que el sha de cada uno se comparaba **sólo consigo mismo**.

El `40/40` era cierto únicamente porque yo había definido el denominador excluyendo lo que me
faltaba. Corregido: se cargan los diez pins, `unanchored` se imprime SIEMPRE, y un solo vector sin
anclar es rojo.

## Fases

| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `oracle_ref` como DATO (`v3/oracle_ref.json`), leído con `git show`, nunca del working tree | ✅ |
| 2 | `v3/kernel/{proof,pin}.py` transcritos de §14 | ✅ |
| 3 | `v3/verify/parity.py` — la cadena de dos eslabones, dos lados | ✅ |
| 4 | Portar `station`/`sequence`/`gate`/`report` (el resto de `kernel/` en §10.2) | ⏳ |

## Criterio de cierre (demostrable, no narrable)

1. `python3 -m v3.verify.parity` verde: 84 vectores, **84/84** estaciones pineadas, 10 líneas,
   `unanchored=0`. ✅
2. `V3_PARITY_SABOTAGE=1` detecta un exit code volteado (el sha se mueve). ✅
3. El oráculo es un COMMIT, no el working tree. ✅
4. Ningún módulo de v3 importa `metafactory` (`import_boundary` verde, 13 módulos). ✅
5. `meta check` sin sexto rojo.
6. Fase 4 cerrada, o diferida con nodo y disparador.

## Fuera de alcance

- Escribir el host — es INC-2, el go/no-go.
- Correr las líneas de verdad (gradle, PG, Chromium): eso es INC-7..INC-9 y **no es hermético**.
  Este incremento prueba que el kernel calcula lo mismo, no que las estaciones sigan pasando.
