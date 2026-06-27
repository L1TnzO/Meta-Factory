<!-- meta:doc sha=db5c19a9d199b35a8cc730cea671167067a70a96 updated=2026-06-27T03:20Z -->
<!-- meta:doc sha=PENDING updated=2026-06-27T03:10Z -->
# Incremento FSK-DIAL-ADOPT — Full-Stack Kotlin · adopción del dial draft→harden

> **Doc de gobierno.** Estado: **CERRADO** (2026-06-27T03:20Z) (creado 2026-06-27T03:00Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).
> **AUTOCONTENIDO A PROPÓSITO.** Asumí que el contexto de la sesión que lo escribió murió. Si algo no está
> acá (o en la spec), no existe. Orden de lectura: §0.

## 0. Si llegás sin contexto, leé en este orden
1. Este doc entero (el plan + la evidencia de la adopción).
2. `docs/work/DRAFT-HARDEN-DIAL-INCREMENT.md` (meta, CERRADO) — el MECANISMO del dial.
3. `docs/work/DIAL-MEASURE-INCREMENT.md` (meta, CERRADO) — el WIRE (tier al materializar) + el gate `dial`.

## Objetivo
ADOPTAR el dial draft→harden en FSK (la 1ª fábrica que lo usa): declarar `tier: harden` en su CAPA DE RIGOR
para que `--mode draft` la difiera y dé un loop de velocidad sobre una app REAL que corre, con `--mode harden`
(default) byte-idéntico al pin. Activa la palanca que `DIAL-MEASURE` dejó cableada (hasta hoy ninguna fábrica
la usaba → `--mode draft` era no-op).

## El cambio (DATA por-fábrica, ADR-012 — cero sustrato)
- **`factory.spec.yml`**: 7 estaciones taggeadas `tier: harden` — la capa de RIGOR + shipping:
  s2 (dureza estática) · s3 (frescura de API) · s4 (cadena de suministro) · s7 (pirámide de tests) ·
  s8 (a11y/perf) · s10 (build hermético) · s11 (deploy docker). El **spine core** (un app que CORRE) queda en
  s0 (scaffold/contrato) · s1 (datos/PG) · s5 (auth/rutas) · s6 (lógica de dominio) · s9 (runtime/observabilidad).
- **`stations/s{2,3,4,7,8,10,11}.yml`**: re-materializadas del spec (m02) → cada una gana `tier: harden` (el
  motor las difiere en draft vía `Station.active_in`). +1 línea por archivo, cero churn (s0 sin tocar).
- **Por qué el split es limpio**: sólo s0 (scaffold completo vía `scaffold_product.py`) y s6 (LLM) GENERAN
  archivos; s2/s3/s4/s7/s8 son estaciones de CHECK sobre el árbol ya scaffoldeado → diferirlas NO quita ningún
  archivo que el spine necesite (sin riesgo de config faltante). La única arista core→harden (s5→s4) cae a
  través (s4 es un gate puro, sin artefacto que s5 consuma; el fall-through del motor lo maneja, probado en
  `test_dial`). s10/s11 (harden) difieren juntas con sus deps.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Taggear `tier: harden` en las 7 estaciones de rigor del spec + re-materializar la línea (m02) | ✅ |
| 2 | Evidencia VIVA por bloqueo: draft corre el spine / harden == pin + el delta medido | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `meta dial` → FSK **ADOPTADO** (5 core + 7 harden; draft corre 5/12, difiere s2,s3,s4,s7,s8,s10,s11);
   el gate `dial` verde (subconjunto propio no vacío). ✅
2. `product-run --mode draft` PASS sobre la app REAL: el spine construye un app que CORRE (server vivo +
   control de acceso + frontend en Chromium) y DIFIERE las 7 de rigor, con rótulo honesto de boceto (no finge
   los gates: la estación diferida no tiene proof). ✅
3. `ci --rederive --all-products` == pin: harden re-deriva BYTE-IDÉNTICO (el `tier` no toca el `proof_sha`) →
   **cero re-pin**. ✅
4. `meta check` 15/15 (`dial ok` ahora refleja FSK adoptado; `column_parity ok`). ✅

## Evidencia (por bloqueo)
- **`meta dial`** → `full-stack-kotlin — ADOPTADO: 5 core + 7 harden (draft corre 5/12, difiere 7: s2,s3,s4,s7,s8,s10,s11)`.
- **`product-run --mode draft`** → PASS (exit 0); última estación s9: `observability_live · access_control_live ·
  frontend_consume_live · frontend_browser_live` verdes (la app CORRE en Chromium vivo); rótulo `DIAL=draft
  (boceto, NO endurecido — 7 estación(es) harden diferida(s): s2,s3,s4,s7,s8,s10,s11)`. **41.7 s**.
- **`product-run --mode harden`** → PASS (exit 0); última estación s11: `deploy_smoke · deploy_appserver_live`
  (rigor completo + deploy docker vivo). **98.0 s**.
- **Delta MEDIDO (narrado, no gateado — wall-clock no re-derivable)**: draft **41.7 s** vs harden **98.0 s** →
  el loop de velocidad ahorra **~56 s (~57% más rápido)** difiriendo la capa de rigor, sobre la app real.
- **`ci --rederive --all-products`** → PASS, **4/4 productos == pin** (default 12/12 · assets 11/11 · helpdesk
  11/11 · snipeit 11/11): harden byte-idéntico, **cero re-pin** (el `tier` no entra al `proof_sha`).
- **`meta check`** → `15 checks all green` (… benchmark ok · **dial ok** · column_parity …).

## Alcance honesto (§7)
El dial trade-ea rigor por velocidad HONESTAMENTE: draft SALTA los 7 gates de rigor (no los finge — no escriben
proof) y el veredicto lo rotula boceto. El valor de dos-lados (harden ATRAPA el rigor que draft salta) está
probado en el motor (`tests/test_dial.py`, DRAFT-HARDEN-DIAL); el diente del gate adoptado (all-harden →
decorativo → rojo) en `tests/test_dial_measure.py` (DIAL-MEASURE). Esta adopción es DATA (cero sustrato): otras
fábricas (dummy/iot/full-stack/ASF) siguen sin adoptar (N/A honesto) hasta que lo elijan. El `s9` (runtime +
observabilidad) se dejó CORE a propósito: draft entrega un app que CORRE (con /health + control de acceso),
no sólo que compila.
