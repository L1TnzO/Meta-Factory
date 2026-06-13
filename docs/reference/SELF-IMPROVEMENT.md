<!-- meta:doc sha=c2df695e6717c9c4969f46175ee757c7a04a04b5 updated=2026-06-13T14:57Z -->
# Auto-mejoramiento seguro — la jerarquía de confianza y el loop

| Campo | Valor |
| --- | --- |
| Documento | Modelo de seguridad del sistema que se mejora a sí mismo |
| Depende de | `VISION.md §3` (el punto fijo), `ARCHITECTURE.md §7` (la jerarquía de stages) |
| Tesis | El auto-mejoramiento es legítimo (PF-9) pero es la operación de MÁS riesgo del ecosistema; recibe la garantía más fuerte, no la más débil |

> El peligro de un sistema que se modifica a sí mismo no es que cambie: es que **cambie sus
> propias compuertas** y, a partir de ahí, mienta sobre todo lo demás. Este doc define cómo el
> Meta-Factory se mejora (y mejora a sus fábricas) sin poder corromper su raíz de confianza.

---

## 1. El problema "trusting trust" aplicado a fábricas

Ken Thompson mostró que un compilador comprometido puede insertar una puerta trasera en lo que
compila —incluido un compilador nuevo— y borrar la evidencia de sí mismo. La analogía exacta
aquí: **un Meta-Factory comprometido podría emitir fábricas con compuertas falsas y, peor,
re-emitirse a sí mismo conservando el compromiso**, de modo que ninguna inspección *local*
lo detecte.

La defensa conocida (David A. Wheeler, *Diverse Double-Compiling*) es no confiar en el binario
sino en la **re-derivación desde una fuente auditada por un verificador independiente**. ASF ya
tenía la pieza correcta —ADR-022, re-derivación sobre custodia— sin nombrar que también es la
defensa contra trusting-trust. El Meta-Factory lo hace explícito y central:

> **No se confía en ninguna fábrica (ni en el Meta-Factory) por lo que dice de sí misma. Se
> confía en que un runner limpio e independiente puede re-derivar su veredicto honesto, idéntico,
> desde la fuente.** Replicable > archivado (PF-10).

---

## 2. La jerarquía de confianza (de más confiable a menos)

```
Stage 0 — SEED CONGELADO            ← raíz de confianza; auditado a mano; pequeño y legible
   │  (verifier, los 3 cerrojos, el workflow de re-derivación externo)
   ▼
CI EXTERNO del Meta-Factory         ← otra máquina, otro actor; re-deriva el dummy-fábrica
   │                                   y exige el veredicto pineado. Intocable por modelo/hooks/ingeniero local.
   ▼
COLUMNA del Meta-Factory            ← hooks/CLI locales (mismo actor); defensa en profundidad, no la raíz
   │
   ▼
CI EXTERNO de cada fábrica producida  → COLUMNA de la fábrica → GATES de cada producto
```

Reglas de la jerarquía (generalizan ASF/ADR-022 §3):

1. **Una capa solo puede ser verificada por una capa al menos tan confiable como ella.** Un
   producto no se auto-verifica; lo verifica la columna de su fábrica. La columna de una fábrica
   no se auto-valida como raíz; la re-deriva su CI externo. Y así hacia arriba hasta el seed.
2. **El seed es la única raíz que NO se deriva de nada.** Por eso es: (a) pequeño —auditarlo por
   ojo humano debe ser factible—; (b) congelado —cambiarlo es Nivel C siempre—; (c) hecho a mano,
   no generado por el Meta-Factory (un sistema no puede ser su propia raíz de confianza).
3. **La única capa que ni el ingeniero, ni el modelo, ni los hooks locales pueden tocar es el CI
   externo.** Es la autoridad del perímetro. Si el Meta-Factory local mintiera, el runner limpio
   computaría un veredicto distinto → rojo.

---

## 3. La regla de oro de la auto-modificación de la cadena de confianza

Modificar `seed/` o la columna (gate/verifier/hooks/commit_guard) es la operación de máximo
riesgo. Recibe el gate más fuerte:

> **Un cambio a la cadena de confianza solo se promueve si el seed VIEJO valida el sistema NUEVO,
> el CI externo re-deriva el veredicto desde un clon limpio, y un revisor de contexto fresco
> (opus) no encuentra fachada ni agujero — y el ingeniero da consentimiento (Nivel C).**

- "El seed viejo valida el nuevo" = la versión confiable actual debe poder probar que la versión
  candidata sigue rechazando un veredicto corrompido (la *prueba de bloqueo*, ASF §21). Si el
  cambio rompe esa prueba, no se promueve. Es el equivalente a re-compilar el compilador nuevo con
  el viejo y comparar.
- El orquestador **lee ese diff con sus propios ojos**, lo haya escrito quien sea (regla
  trust-chain de ASF/ADR-020, generalizada y ahora con sombra: el reviewer va a opus por dato,
  cerrando W4 — ver `CONTEXT-ECONOMY.md §enrutamiento`).
- Cambios que NO tocan la cadena de confianza (una estación nueva, un template de dominio, una
  capacidad de producto) siguen el loop normal (§4) sin el gate reforzado.

---

## 4. El loop: observar → proponer → verificar → promover → rollback

Hereda el `generar→verificar→promover` de ASF (V2.3) y lo completa con las dos piezas que el
estado del arte (ECC 2.0: `stanford-iris-lab/meta-harness`, `greyhaven-ai/autocontext`) aporta:
**guardar la traza+artefacto, no solo el archivo final**, y **el rollback con control de
blast-radius**.

| Fase | Qué pasa | Determinista o juicio | Artefacto que deja |
| --- | --- | --- | --- |
| **Observar** | un gap o oportunidad: RTM UNSATISFIED, un scenario rojo, una entrada del journal, un pedido del ingeniero | determinista (detección de hechos) | `improvement_request.json` (firma del scenario, invariantes a preservar) |
| **Proponer** | la capa inteligente (orquestador/writer) drafta el cambio **como diff + scenario-spec + traza**, no solo el archivo | juicio (modelo), revisable en diff | la traza y el candidato guardados ANTES de mutar nada instalado |
| **Verificar** | corren las gates deterministas; para trust-chain corre la re-derivación externa; un reviewer fresco caza fachada; el **gate de blast-radius** exige que ninguna fábrica downstream baje su veredicto pineado | determinista (gates) + juicio (reviewer) | `proof.json`, reporte del reviewer, diff de veredictos pineados |
| **Promover** | solo si TODO pasa, el patrón/cambio asciende al repertorio (o al seed, con la regla de oro §3); el veredicto pineado se actualiza **por diff revisado**, nunca espontáneamente | determinista (promoción gateada) | el patrón en el repertorio + el commit con trailers |
| **Rollback** | toda promoción es un checkpoint; una regresión en el CI externo de cualquier fábrica downstream dispara reversión | determinista | el revert + entrada en LOG |

**El gate de blast-radius** (de autocontext, *"promote only after a verifier proves improvement
without widening blast radius"*): una mejora al Meta-Factory que pretende ayudar a una fábrica no
debe degradar a otra. Se materializa así — el CI externo del Meta-Factory re-deriva el
dummy-fábrica Y corre los CI externos de las fábricas producidas (o sus veredictos pineados); si
alguno baja, la promoción es roja aunque el cambio "mejore" su objetivo. Una "mejora espontánea"
sin diff revisado es una fachada, no una mejora (ASF/ADR-022).

---

## 5. Niveles de riesgo de la auto-modificación (qué gate recibe cada cambio)

| Riesgo | Qué se modifica | Gate aplicado |
| --- | --- | --- |
| **R0 — Bajo** | un template de dominio, una capacidad de producto, una estación nueva en una fábrica | loop normal §4 (gates + reviewer sonnet) |
| **R1 — Medio** | la maquinaria del Meta-Factory (engine, codegen, spec) sin tocar la columna | loop §4 + reviewer; CI externo re-deriva |
| **R2 — Alto** | la columna de una fábrica producida (sus hooks/gates) | regla de oro §3 aplicada a esa fábrica; su CI externo re-deriva; consentimiento |
| **R3 — Máximo** | el `seed/` o la columna del **Meta-Factory mismo** | regla de oro §3 completa: seed-viejo-valida-nuevo + re-derivación externa + reviewer opus fresco + consentimiento humano; congelado por defecto |

El diseño no impide equivocarse; hace que equivocarse **cueste poco hacia abajo y muchísimo
hacia la raíz** — exactamente donde debe estar la fricción. Sub-delegar o sobre-delegar un R0 se
recupera barato (ASF/ADR-020); tocar el seed sin la ceremonia R3 simplemente no se promueve.

---

## 6. Por qué esto NO es teatro (la lección de ADR-023)

ASF aprendió que **forzar juicio con un hard-block produce el ritual, no el contenido**
(ADR-023: "forzar sería teatro"). El modelo de §1–§5 respeta eso:

- Lo que se **hard-blocka** es siempre un HECHO determinista: un veredicto corrompido, un hash que
  no coincide, una re-derivación que difiere, un veredicto pineado que baja. Nunca un juicio.
- Lo que requiere **juicio** (¿es esta mejora buena? ¿el reviewer ve una fachada?) se gobierna por
  modelo + revisable-en-diff + consentimiento, y se *mide* (el contador de delegaciones, el
  journal), no se fuerza.
- La sombra determinista (PF-11) está del lado de la *detección*, no de la *coerción del juicio*.
  Detectar que el STATE quedó viejo: determinista. Decidir qué escribir en él: modelo.

Ésa es la frontera que hace que el auto-mejoramiento sea seguro sin ser ritualista.
