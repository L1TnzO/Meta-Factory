<!-- meta:doc sha=07a38b296a0b422f9261125e915b4aa58f089997 updated=2026-07-31T19:08Z -->
# Incremento FREEZE-AUDIT-ANCHOR

> **Doc de gobierno.** Status: **OPEN** (creado 2026-07-31T19:03Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Bajar el último rojo de la suite atacando sus **dos** causas, que son distintas y sólo comparten gate:
legislar `ba05918` en `WAIVED_COMMITS` (acto de gobierno, con ojos) y **anclar el parser del waiver**,
que hoy lee una MENCIÓN en prosa como declaración malformada.

## Contexto — por qué son dos cosas y no una
`codegen_freeze` estaba rojo por dos motivos independientes que se leían como uno:

1. **`ba05918` (13-07)** alimentó el codegen congelado sin waiver. **No se puede reparar hacia atrás:** la
   auditoría histórica pregunta si el commit llevaba, **en su PROPIO árbol**, un work-doc ABIERTO con
   waiver válido. Ningún texto escrito hoy cambia el árbol de un commit de hace 18 días. O se legisla, o
   el gate queda rojo para siempre sobre una condición inalcanzable — que es exactamente como un rojo
   deja de leerse.
2. **La línea 75 de `FSK-EVALUATOR-ADOPT`** —un residual con disparador que MENCIONA el vocabulario en
   medio de una oración— se reportaba como «waiver MALFORMADO». La regla era **inescribible en sus
   propios documentos de gobierno**: nombrarla en prosa ponía roja a la fábrica. Esta causa desapareció
   sola cuando ese incremento cerró, y ahí está lo interesante: **el defecto se habría borrado sin
   arreglarse**. Por eso la prosa se dejó INTACTA como testigo hasta ahora.

## Diseño
- **`WAIVED_COMMITS[ba05918…]`** con la razón ESCRITA en el propio diccionario (donde la va a leer quien
  audite, no en un doc aparte): qué alimentó, por qué revertirlo habría sido cambiar corrección por
  conformidad, y que queda **grandfathered, NO absuelto** (aterrizó bajo un incremento de otro sujeto,
  `N-0105`, y dejó la fábrica roja 18 días). El diff en sí ya volvió a conformidad por
  `FSK-JSONVAL-DETEKT`, que sí declaró su waiver en árbol.
- **`_DECL_RE`**: una DECLARACIÓN es una línea que **ABRE** con el token (tolerando viñeta/cita/negrita).
  **El argumento de seguridad para angostar un check de seguridad es que el angostamiento es
  fail-CLOSED:** el ancla sólo puede QUITAR líneas de consideración, nunca inventar un waiver. Una
  declaración real que no ancle deja de contar → su diff queda sin cobertura → **rojo**. El peor caso es
  una falsa ALARMA, nunca un pase silencioso — la única dirección en la que a un gate de congelamiento se
  le permite equivocarse.
- **Tres escenarios sintéticos nuevos** (3 → 6), porque un ancla sin diente se afloja sola: una MENCIÓN
  sin diff debe PASAR · una mención CON diff debe seguir roja (mencionar no cubre) · un waiver con
  viñeta/negrita debe SEGUIR contando (que el ancla no se pase de estricta). El texto de la mención es el
  **testigo real** de la línea 75, verbatim, no una hipótesis.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `WAIVED_COMMITS` + ancla `_DECL_RE` + 3 escenarios rojos nuevos | ✅ |
| 2 | `meta check` **23/23** | ✅ §Evidencia |

## Criterio de cierre (demostrable, no narrable)
1. `codegen_freeze` verde **con la auditoría histórica corriendo** (no salteada) y **6 escenarios
   sintéticos vivos**, no 3.
2. `meta check` **23/23** — el rojo que quedó de INC-9 baja a cero.
3. La suite de tests del gate sigue verde (13 casos), y el ancla NO afloja: los tres escenarios nuevos
   fallan si alguien vuelve a confundir prosa con ley, en cualquiera de las dos direcciones.
4. `git diff` acotado a `src/metafactory/verify/checks/codegen_freeze.py` + este doc: **cero** cambio en
   fábricas, codegen o pines. Este incremento no toca un producto.

## Evidencia (medida 2026-07-31)
```
OK codegen_freeze: 4 fábrica(s) con codegen/ congelado sin alimentación no-waivereada;
   auditoría histórica: 1 commit(s) post-epoch 4bd9835c5 auditado(s); diente RED vivo (6 escenarios)

meta check → PASS (exit 0) · 23 checks all green
pytest -k "freeze or waiver" → 13 passed
```

Tres cosas que vale la pena dejar dichas:

1. **La auditoría histórica sigue CORRIENDO, no salteada.** Reporta «1 commit post-epoch auditado»: el
   waivereado se saltea, pero el otro commit del período —`4db7f0d`, el arreglo de `FSK-JSONVAL-DETEKT`—
   **se auditó y pasó por sus propios medios**, porque declaró su waiver en el árbol que introdujo el
   diff. Si el diccionario hubiera apagado la auditoría en vez de exceptuar un sha, ese 1 sería 0 y nadie
   lo notaría.
2. **El ancla se probó en las dos direcciones.** No alcanza con «la mención ya no molesta»: si el ancla se
   pasa de estricta, un waiver legítimo escrito con viñeta o negrita deja de contar y el gate empieza a
   ladrar sobre diffs cubiertos. Los tres escenarios cubren mención-sin-diff (pasa), mención-con-diff
   (roja) y declaración-adornada (cuenta).
3. **La suite estaba en 19/23 al empezar la sesión y queda en 23/23.** De los cuatro rojos, tres eran
   consecuencia de un solo producto roto (`N-0103`) y el cuarto es este. Ninguno se apagó bajando una
   barra: el producto se arregló, la STATE se podó al presupuesto que el diente pide, y acá se legisló un
   commit con la razón escrita al lado del sha.
