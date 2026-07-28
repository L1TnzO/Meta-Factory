<!-- meta:doc sha=f0f5beb5dd9c1df31aac458b9f9dfe94c44e4265 updated=2026-07-28T17:43Z -->
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
| 4 | `station` · `sequence` · `gate` · `report` — `kernel/` completo (6 módulos de §10.2) | ✅ |

### Fase 4 — el segundo oráculo hermético, y por qué vale

`parity.py` prueba que el kernel calcula la misma IDENTIDAD de estación. `line_parity.py` prueba que
calcula la misma LÍNEA: qué estaciones existen, cuáles están activas y en qué orden corren. Otra vez
dos eslabones, porque uno solo sería auto-referencial:

1. **Conjunto activo** — parsear los 41 YAML de estación commiteados, quedarse con los
   `active_in(harden)`, y el resultado debe igualar el conjunto de claves del pin commiteado.
   Ya se ganó el sueldo: `agent-systems-factory` tiene **13** archivos de estación y pinea **12**,
   porque su `s0` lleva `activation: 'off'`. Un port que ignorara la activación daría 13 ≠ 12 acá.
2. **Orden natural** — donde la línea llega a dos dígitos, `s9` debe preceder a `s10`. El orden
   lexicográfico pone `s10` primero, y ese defecto sólo aparece en las líneas más largas: justo los
   productos que más importan. Se afirma sobre nombres de archivo reales, no sobre un fixture.

Medido: **41 estaciones · 40 activas · 1 apagada**, en 5 líneas, coincidiendo exacto con los pins.
El sabotaje apaga una estación activa: el conjunto pierde una que el pin sigue cargando y el gate
enrojece — que es el caso «una estación desapareció en silencio» que `pin_matches` llama desviación
y no tolerancia.

`report.py` deja de ser un formato de texto y pasa a ser un TIPO: `status` se deriva de `exit_code`,
así que no pueden discrepar, y el render no puede pasar de 10 líneas — **y cuando trunca, lo dice**.
Una truncación silenciosa es cómo un bus deja de ser evidencia y se vuelve un resumen de sí mismo.
`line_parity` lo usa, que es la prueba de que sirve.

`gate.py` compone los cerrojos **decidibles desde datos** (1 y 2) y dice en su docstring que el 3
—el cierre de turno— es del host y vive en INC-2. Un archivo que dijera «los tres cerrojos»
implementando dos sería exactamente la media verdad que los cerrojos existen para atrapar.

## Criterio de cierre (demostrable, no narrable)

1. `python3 -m v3.verify.parity` verde: 84 vectores, **84/84** estaciones pineadas, 10 líneas,
   `unanchored=0`. ✅
2. `V3_PARITY_SABOTAGE=1` detecta un exit code volteado (el sha se mueve). ✅
3. El oráculo es un COMMIT, no el working tree. ✅
4. Ningún módulo de v3 importa `metafactory` (`import_boundary` verde, 13 módulos). ✅
5. `meta check` sin sexto rojo.
6. Fase 4 cerrada: `kernel/` completo (`proof · pin · station · sequence · gate · report`) y
   `line_parity` verde en ambos lados (41 estaciones · 40 activas · 5 líneas). ✅

## Fuera de alcance

- Escribir el host — es INC-2, el go/no-go.
- Correr las líneas de verdad (gradle, PG, Chromium): eso es INC-7..INC-9 y **no es hermético**.
  Este incremento prueba que el kernel calcula lo mismo, no que las estaciones sigan pasando.
