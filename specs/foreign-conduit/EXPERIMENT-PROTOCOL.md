# E1+D-8 · Protocolo del grupo de control (COUNCIL-360 §6.4.4) — escrito ANTES de correr

> Regla anti-sesgo: este protocolo se commitea ANTES de ejecutar cualquiera de los dos brazos.
> El resultado se registra SEA CUAL SEA (un rojo del brazo-fábrica es un hallazgo D-8, no un fracaso
> a esconder).

## Pregunta
¿Qué entrega la FÁBRICA frente a un agente PELADO (sin fábrica) ante una spec AJENA (no escrita en
nuestra gramática ni por nosotros), al mismo presupuesto acotado? Decide la historia de VALOR (E1) y
falsifica la endogeneidad del benchmark (D-8).

## Spec de entrada (idéntica para ambos brazos)
`specs/foreign-conduit/` — RealWorld «Conduit» backend spec, verbatim de terceros
(gothinkster/realworld @98f29fb3, ver PROVENANCE.md).

## Brazo A — fábrica (FSK)
1. Traducción spec→`product.yml` en ESTA sesión, con **bitácora de fricción** (cada concepto de la
   spec que la gramática NO expresa se anota, no se maquilla): `TRANSLATION-NOTES.md`.
2. `meta product new conduit` + `meta product-run conduit --mode draft` (línea 0-modelo).
3. Se registra: resultado de la línea (verde/rojo y dónde) · RTM del producto · veredicto del
   benchmark sweet-spot aplicado a conduit · wall-clock.

## Brazo B — control pelado
1. UN generator (Sonnet) en worktree AISLADO, misma spec verbatim, presupuesto acotado (≤35k tokens,
   ≤25 min), instrucción: «backend Conduit funcional con persistencia + tests, stack libre».
2. Se registra: qué entrega · sus tests corren y pasan (verificado por NOSOTROS, no narrado) ·
   wall-clock/tokens.

## Arbitraje (la misma vara para ambos)
Checklist de capacidades VERIFICADAS (no narradas), derivado del benchmark sweet-spot:
| Capacidad | Cómo se verifica |
| --- | --- |
| persistencia viva (CRUD contra DB real) | brazo A: gates s1; brazo B: correr sus tests/su server |
| autorización (roles o identidad) | brazo A: s5 rbac/ownership; brazo B: inspección + tests propios |
| workflow/estado | brazo A: s7; brazo B: ídem |
| control de acceso en server VIVO | brazo A: s9; brazo B: request real si hay server |
| frontend que renderiza | brazo A: s9 frontend; brazo B: ídem |
| re-derivabilidad (¿se reconstruye igual desde la spec?) | brazo A: pin; brazo B: N/A estructural |
| tasa de escape conocida | E4 (solo brazo A tiene el instrumento) |

## Límites DECLARADOS del diseño (honestidad metodológica)
- n=1, un solo dominio, un solo presupuesto — es un PRIMER punto de datos, no un paper.
- El «CC pelado» es un subagente Sonnet con presupuesto de slot, no una sesión interactiva con humano
  — subestima al brazo B en iteración, lo sobreestima en foco (sin distracción de contexto).
- La traducción spec→product.yml la hace el MISMO agente que opera la fábrica (sesgo pro-A posible
  en fidelidad de traducción); mitigación: TRANSLATION-NOTES registra TODO lo no-expresable.
- Fricciones ya anticipadas de la gramática (se confirman o refutan al correr): sin campos-lista
  (tagList → entidades join) · sin M2M nativo (follow/favorite → entidades) · la spec ajena NO tiene
  workflow (el benchmark exige `workflow_enforced` → conduit puede quedar fuera del sweet-spot POR
  DISEÑO del benchmark, y ESO es un hallazgo D-8 sobre el benchmark, no sobre conduit).
