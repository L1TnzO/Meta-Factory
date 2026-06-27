<!-- meta:doc sha=002c1feb62a7c74e0c6c8b862dec0d81b500d265 updated=2026-06-27T21:52Z -->
# Incremento DELEG-TOPOLOGY-HYGIENE

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-27T21:46Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
**Higiene de topología** de la delegación + **cierre** del incremento-familia `DELEGATION-ACTIVATION`: la
decisión `verifier`-vs-`Explore` tomada y registrada (D1), la regla **«especializar por ROL, nunca por dominio»
escrita CON DIENTES** (D2, gate `roles`), la convergencia de nombres de rol resuelta (forward-only, sin churn),
y la decisión de arquitectura fijada en **ADR-020** (a)–(d). Fase **D** (última) de `DELEGATION-ACTIVATION`
(B `DELEG-MEASURE` ✅ + A `DELEG-ACT-META` ✅ + C `DELEG-ACT-FACTORY` ✅). Detalle:
`work/DELEGATION-ACTIVATION-DIRECTION-INCREMENT.md §4 Fase D` + §5.2.

## Contexto
Con A·B·C, el meta delega NATURALMENTE, la métrica MIDE, y las 5 fábricas heredan el cerebro. Quedaba la
**higiene**: (i) ¿el `verifier` custom (Haiku read-only) es redundante con el built-in `Explore`?; (ii) la
trampa que el ingeniero intuyó — proliferar agentes **por dominio** (`kotlin-writer`, `frontend-generator`) —
no tenía diente; (iii) los dos vocabularios de rol (meta `generator`/`verifier` ↔ fábrica `writer`/`triage`)
sin un modelo mental único. D los cierra **sin maquinaria nueva de peso**: un gate determinista + governance +
un ADR inmutable. Todo D es **columna/trust-chain** (agents, gates, vocabulario, governance) → ojos propios,
la excepción explícita de la regla de delegación.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| D1 | **`verifier` vs `Explore`: KEEP, con la razón registrada.** `Explore` es búsqueda fan-out que LOCALIZA leyendo excerpts y «no revisa ni audita»; el `verifier` lee UN artefacto conocido EN COMPLETO (log de gate / árbol / spec) y devuelve un digest estructurado. Complementarios, no redundantes → se mantiene. Registrado en `verifier.md` (§«Why you exist»), `orchestrator.md` (la regla de ruteo `Explore` vs `verifier`) y ADR-020 §D1. | ✅ |
| D2 | **Regla «especializar por ROL, no por dominio» CON DIENTES.** `agent_roles.py` (single-source, espeja `column_scope.py`): vocabulario CERRADO `CANONICAL`={orchestrator·generator·verifier·reviewer} + `LEGACY_SYNONYMS`={writer≡generator·triage≡verifier}. Gate **`roles`** (`role_hygiene.py`, dos-lados): escanea los 24 agents (meta + 5 fábricas), un NOMBRE de rol fuera del vocab (p.ej. `kotlin-writer`) cae a rojo; el negativo sintético muerde. Cableado a `meta check` (#17). Regla en `CLAUDE.md §Reglas`. Agregar un rol = editar el constante + ADR (deliberación = el diente). | ✅ |
| D3 | **Convergencia de nombres de rol: documentada + enforzada, sin churn.** Las 5 fábricas existentes mantienen `writer`/`triage` (cuerpos español; ADR-017 prohíbe re-autorar/traducir en masa + churnear sha-stamps); la equivalencia de rol está en `LEGACY_SYNONYMS` (un solo modelo mental) y el gate `roles` la acepta. La convergencia FÍSICA (renombrar el emisor + re-emitir las 5) es un incremento de fábrica aparte, opcional (residuo honesto). | ✅ |
| D4 | **ADR-020 + cierre del DIRECTION.** `decisions/020` fija (a) routing por `CLAUDE.md` no `agent` global · (b) la `delegation`+split de tokens como KPI de costo · (c) rol-no-dominio con diente · (d) la observabilidad de delegación NO baja a `FACTORY_COLUMN`. Cierra `DELEGATION-ACTIVATION` (STATE «Ahora» + LOG + ROADMAP). | ✅ |

## Decisiones (los juicios que tomé — marcados por si querés revisarlos)
1. **`verifier` se MANTIENE (D1).** No es proliferación: `Explore` (búsqueda fan-out, lee excerpts, no audita)
   y `verifier` (digest-en-completo de UN artefacto conocido) agregan restricciones DISTINTAS. La best-practice
   «apoyate en built-ins, custom sólo si agrega restricción real» se cumple manteniéndolo CON la razón
   registrada — que es la salida que el DIRECTION D1 bendice («si agrega un contrato de digest → documentalo»).
2. **El diente de D2 chequea el NOMBRE de rol, no la descripción.** El nombre ES la identidad de rol (el router
   la registra); una fábrica MENCIONA su dominio en prosa legítimamente (el `orchestrator` sirve a una fábrica).
   El vocabulario CERRADO es la ley: un agente especializado por dominio recibe un nombre fuera del set → rojo.
   Subsume el chequeo «sin token de dominio» sin falsos positivos sobre la residencia.
3. **Convergencia DOCUMENTADA, no física (D3).** Renombrar `writer`/`triage`→`generator`/`verifier` en las 5
   significaría re-autorar 5 agents ESPAÑOLES existentes (contra ADR-017 forward-only) o un híbrido raro
   (nombre inglés, cuerpo español) + churn de artefactos. El gate funciona con AMBOS vocabularios (sinónimos
   legacy declarados), así que el «un modelo mental» se logra con la equivalencia + el diente, sin el churn —
   alineado con el ethos anti-churn del proyecto y con mi juicio #2 de la Fase C (que difirió el rename acá).
   Si preferís la convergencia física, es un incremento de fábrica aparte; decímelo.
4. **CREÉ el ADR-020 ahora (a diferencia de A y C, que lo difirieron).** Es el momento correcto: con D, las
   decisiones (a)–(d) del §5.2 están TODAS resueltas (a/b de A, d de C, c de D). Crearlo antes habría sido un
   ADR parcial superseable (el churn de historia prohibido); crearlo al cierre lo deja inmutable y completo.
5. **`roles` es meta-only (no baja a fábrica).** El gate escanea meta + `factories/*` DESDE el meta operador
   (es un check de `meta check`); no es un hook de columna de fábrica. Coherente con (d): la higiene de
   topología se gobierna desde arriba, igual que la observabilidad.

## Lo honesto (no lo tapé)
- **Activación viva (igual que A y C):** los `description` afiladas y la regla nueva de `CLAUDE.md` cargan al
  inicio de sesión; D agrega el DIENTE (`roles`) que es verificable AHORA (`meta check` 17/17), pero el ruteo
  proactivo `Explore`-vs-`verifier` lo ejercés en una sesión nueva. D es columna/codegen → ojos propios.
- **Residuo declarado: convergencia física de nombres.** Las 5 fábricas siguen con `writer`/`triage`. Es la
  decisión D3 (forward-only, ADR-017), no un olvido — el gate `roles` lo acepta vía `LEGACY_SYNONYMS`.
- **Sin re-pin:** D no toca codegen/seed/products. `ci --rederive` (spot dummy 5/5 == pin) intacto; `meta check`
  re-deriva las columnas de fábrica (`column_parity`/`least_priv` verdes).

## Criterio de cierre (demostrable, no narrable)
1. ✅ La decisión `verifier`-vs-`Explore` está TOMADA (KEEP) y REGISTRADA (`verifier.md` + `orchestrator.md` +
   ADR-020 §D1).
2. ✅ La regla rol-no-dominio está en governance (`CLAUDE.md §Reglas`) **con diente**: gate `roles`
   (`role_hygiene`) en `meta check`, dos-lados (un agent nombrado por dominio cae a rojo; el negativo muerde).
3. ✅ `meta check` **17/17** (suma `roles`; `generality`/`quality`/`column_parity`/`least_priv` sin regresión).
4. ✅ `tests/` verde incl. `test_role_hygiene` (vocabulario, 24 agents reales, negativo con dientes).
5. ✅ Sin re-pin: `ci --rederive` (dummy 5/5 == pin); D no toca la línea de producto ni el emisor.
6. ✅ ADR-020 inmutable fija (a)–(d); `DELEGATION-ACTIVATION` cerrado (STATE «Ahora» + LOG + ROADMAP).
