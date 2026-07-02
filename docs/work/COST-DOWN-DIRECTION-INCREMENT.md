<!-- meta:doc sha=b7e388693b3bb0ee070869b7e851d1f6a9a58309 updated=2026-07-02T14:33Z -->
# Incremento COST-DOWN-DIRECTION

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-02T14:30Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

> **ESTE DOC ES LA BIBLIA DE COSTOS.** Documento FUNDACIONAL y AUTO-CONTENIDO de la dirección
> `COST-DOWN` (ADR-021): cómo hacer que la Meta-Factory y las fábricas cuesten 3–5× menos por incremento
> (~10× en el día-a-día) SIN perder potencia — mismas garantías (pin de clon limpio, gates, RTM), otro precio.
> El plan es **FIJO: N=7 incrementos (INC-0…INC-6), orden inmutable, condiciones de N/A pre-decididas** —
> las sesiones futuras EJECUTAN, no re-deciden. Una sesión que llega sin contexto necesita SOLO este doc.

## Cómo leer este doc (regla de rebanada — el doc practica lo que predica)
- **Siempre:** §2 (la doctrina, ~60 líneas) + §4.INC-n (la spec del incremento que te toca).
- **Referencia, NO lectura obligatoria:** §1 (evidencia medida) · §3 (catálogo de palancas) · §5–§6.
- No leas el doc entero en una sesión de ejecución: `grep -n "INC-<n>"` y andá a tu rebanada.

## Objetivo (de ESTE incremento de dirección)
Cristalizar la dirección de economía en un **ADR-021** + esta biblia auto-contenida con el plan fijo de
7 incrementos, para que las próximas sesiones sepan QUÉ construir, EN QUÉ ORDEN y CUÁNDO PARAR — sin re-diseñar.

---

## §1 · POR QUÉ — la evidencia medida (2026-07-02; no re-derivar, está citada)

### 1.1 La factura y el fracaso instructivo
- **$2,761.18 en 32 sesiones (~$86/sesión) · split opus 89% · sonnet 11% · haiku 0%** (`meta metrics`).
- La delegación por slots (Fase 2 SOTA, encendida en ADR-020) **no movió la aguja**: se delegaron **159k tok**
  a Sonnet (`DELEG-PAYOFF-MEASURE`) y la delegación acumulada quedó en **0.06%** (3 eventos vs 5,225
  station_run). Causa raíz: la delegación ataca el OUTPUT de Opus, pero el costo real es su **RESIDENCIA**
  (turnos × contexto re-leído del cache) — el orquestador Opus siguió pagando alquiler en cada turno mecánico.
- Turnos mecánicos medidos: **Bash 6,170 · Read 3,496 · Edit 2,430 · Write 427** (acumulado 32 sesiones).
- Churn de contexto: **66 archivos re-leídos, 156 re-lecturas EXTRA** (`server.py`×20 · `base.py`×13 ·
  `constants.py`×13) · **3 compactaciones** en un solo incremento.
- Slot peor-caso: gen#1 = 73k tok / **79.5 min** (huecos > TTL de cache garantizados); el gate de iteración
  era `product-run snipeit` (integración de minutos, 19 entidades) — el oráculo "barato" que no lo era.
- Rehidratación de sesión (SessionStart): **~500 tok** (prom 539). Matar-y-renacer una sesión cuesta CENTAVOS.

### 1.2 La tabla de precios (DATA, 2026-07-02, USD/MTok — actualizar acá si cambia)
| Modelo | Base input | Write 5m | Write 1h | **Hit & refresh** | Output |
| --- | --- | --- | --- | --- | --- |
| Opus 4.8 | $5 | $6.25 | $10 | **$0.50** | $25 |
| Sonnet 5 (promo hasta **2026-08-31**) | $2 | $2.50 | $4 | $0.20 | $10 |
| Haiku 4.5 | $1 | $1.25 | $2 | $0.10 | $5 |

Ratios estructurales: **opus:sonnet:haiku = 5:2:1 uniforme** · hit = 10% del base · write 5m = 1.25× ·
write 1h = 2×. **El thinking factura como OUTPUT** ($25/M en Opus): un turno mecánico con thinking alto es
plata quemada. ⚠️ Re-evaluar el ruteo cuando venza la promo de Sonnet 5 (2026-09-01).

### 1.3 Descomposición de una sesión tipo (reconstrucción; INC-1 la hace EXACTA)
Sesión representativa (~400 turnos, ctx medio 140k, output+thinking ~2.5k/turno, 3 expiraciones, 1 compactación):
| Término | Cálculo | ~$ | ~% |
| --- | --- | --- | --- |
| Cache-hits (turnos × ctx) | 400 × 140k × $0.50/M | $28 | **~45%** |
| Output + thinking Opus | 400 × 2.5k × $25/M | $25 | **~40%** |
| Expiraciones + compactación | 3×140k×$6.25/M + ~$1.5 | $4 | ~7% |
| Writes incrementales | 180k × $6.25/M | $1 | ~2% |
**Lectura:** la factura es `turnos × contexto` + `turnos × verbosidad`, mitad y mitad. El churn de cache (la
pregunta del TTL) es REAL pero tercer orden (~5–15%). Las palancas del 85% son: ruteo de modelo por sesión,
contexto chico, menos turnos.

### 1.4 Tres hechos verificados en el repo (2026-07-02, con ojos)
1. **`src/metafactory/graph/billing.py` precia solo con `(input, output)`** — el ledger es CIEGO a las 3
   columnas de cache que queremos optimizar. Sin INC-1, ninguna decisión de cache es decidible.
2. **La línea FSK no llama a NINGÚN modelo** (grep en `stations/` y `codegen/`): `product-run` es 100%
   determinista. El costo del día-a-día es la SESIÓN Opus que lo babysittea, nunca la línea. → El día-a-día
   se arregla con una REGLA (INC-0), no con código.
3. El arnés verificar-no-revisar (radios por hook · veredicto obligatorio · retry ≤2 · pin de clon limpio ·
   `increment_guard`/`stop_proof`) YA hace que la correctitud NO dependa del modelo del ejecutor.

---

## §2 · QUÉ — la doctrina (economía Opus-marginal, ADR-021)

### 2.1 Principio rector
> **La correctitud la dan los GATES, no el IQ del ejecutor.** El modelo de cada sesión/turno es un parámetro
> de PRECIO, no de seguridad. El juicio caro (Opus) se gasta SOLO donde no hay gate: diseñar contratos,
> decidir alcance, revisar el residuo irreducible, y la COLUMNA (trust-chain, con ojos propios).

### 2.2 Ruteo por SESIÓN (la extensión de ADR-017 §3 un nivel arriba)
| Clase | Modelo | Forma | Entrega |
| --- | --- | --- | --- |
| **S1 · DISEÑO** | Opus, thinking alto | corta (≤~30 turnos; matar antes de 100k ctx) | el plan como DATA (`.gen/plan.json`, INC-4) — contratos, gates, radios, criterios |
| **S2 · EJECUCIÓN** | **Sonnet** (`claude --model sonnet --agent orchestrator`) | la que haga falta (turnos 2.5× más baratos) | commits + veredictos; en rojo-persistente/seguridad/ambigüedad → archivo de escalación, NUNCA "pensar más fuerte" |
| **S3 · REVISIÓN/CIERRE** | Opus, corta | muy corta | lee outcome+veredictos+escalaciones, revisa residuo, cierra, handoff |
- **Día-a-día** (producto desde spec existente): shell directo o Sonnet — **NUNCA Opus** (§1.4-2).
- Sin rol nuevo: `orchestrator` con el modelo como parámetro de invocación (vocabulario ADR-020 intacto).
- Peor caso de un ejecutor Sonnet = tokens 2.5× más baratos desperdiciados; jamás código malo aceptado
  (gates) ni fuera de radio (hooks) ni cierre sin prueba (`stop_proof`). Riesgo acotado por retry ≤2 +
  escalación barata.

### 2.3 Doctrina de cache (la respuesta cerrada a "¿5m o 1h?")
**Mecánica:** cada hit REFRESCA el TTL al precio del hit ("Hits & Refreshes"). El cache NO muere por duración
de la tarea; muere por un **HUECO > TTL sin requests**. La variable es la distribución de huecos.
**Matemática** (P = prefijo cacheado, C = contexto total escrito en la sesión, b = precio base):
- Penalidad de UNA expiración (política 5m): re-write `1.25b·P` en vez de hit `0.1b·P` → **≈ 1.15b·P extra**.
- Sobrecosto de la política 1h: 2× en vez de 1.25× por CADA token escrito → **≈ 0.75b·C total**.
- **Regla:** 1h conviene ⟺ `E[huecos>5min] × 1.15·P > 0.75·C`; con P≈C ⟺ **esperás ≥1 hueco >5min**.
- Verificación de intuición: 2 writes 5m = 2.5b·P > 1 write 1h = 2b·P — una sola expiración ya paga el 1h.
- En números (P=120k, Opus): hit $0.06 · expiración $0.75 · premium 1h/sesión (C=160k) ≈ $0.60.
**Decisión (DATA, no opinión):** sesiones de trabajo real (gradle en minutos, slots 15–79 min medidos) tienen
huecos >5min con certeza → **TTL 1h SI el knob existe**; 5m alcanza solo para sesiones cortas que MORÍS al
terminar. ⚠️ Claude Code hoy NO expone el knob (la API sí: `cache_control {ttl:"1h"}` + beta
`extended-cache-ttl-2025-04-11`) — el sondeo y el camino proxy son INC-5, condicional por medición.
**Las 3 cartas que le ganan al TTL (usarlas SIEMPRE, no requieren knob):**
1. **Hueco al FINAL → matar la sesión.** Rehidratar cuesta ~500 tok (~$0.003). Nunca "dejarla abierta por las dudas".
2. **Hueco DURANTE (gate/slot corriendo) → keep-warm**: gate en `run_in_background` + turno de poll cada
   ≤4 min = 0.1×P por poll — **12.5× más barato que expirar**. (Mejor aún: slot headless, INC-6 → residencia $0.)
3. **Compactación = INCIDENTE, meta 0**: re-write total + re-lecturas frías; matar-y-rehidratar la domina siempre.

### 2.4 Doctrina de contexto y verbosidad
- **Thinking dial:** alto SOLO en S1; medio/bajo en S2 y turnos mecánicos (thinking = output $25/M).
- **Abstract-first:** la respuesta default a "¿qué hace X?" es el abstract del grafo (firma+docstring+deps),
  no el archivo. Lecturas masivas → `verifier` (Haiku, 5:1) / `Explore`. Docs → por rebanada (`grep`/§), jamás enteros.
- **Prefijo estable:** no editar CLAUDE.md/agents/settings a mitad de sesión (invalida el cache desde ahí).
- **Salida de gates = 1 línea + artefacto** (patrón `VEREDICTO`): stdout verboso infla TODOS los turnos siguientes.

### 2.5 Calibración honesta (lo que NO prometo)
- **Piso irreducible ≈ 20–30% del gasto actual** a igual throughput: S1 + S3 + escalaciones + columna-con-ojos.
  La promesa es 3–5× por incremento y ~10× SOLO en la clase día-a-día determinista. No 10× global.
- Con la tabla nueva, el ruteo Opus→Sonnet da **≤2.5×** (no 5×). La ganancia grande es MULTIPLICATIVA:
  ruteo (≤2.5×) × contexto-lean (1.5–2.5×) × menos-turnos (1.3–2×) × higiene-de-cache (1.1–1.2×).

---

## §3 · CÓMO — el catálogo completo de palancas (referencia; cada una mapeada a su INC)

Marcas: ✅ existe · 🔧 se construye en el INC indicado · 📏 sondeo/medición. Ahorro sobre el término que ataca (§1.3).

**A · Precio** — elegir el precio por token
| # | Palanca | Mecanismo → efecto | Estado |
| --- | --- | --- | --- |
| A1 | TTL 1h en sesiones de trabajo | regla §2.3; knob hoy inexistente en Claude Code | 📏 INC-5 |
| A2 | Keep-warm poll en huecos internos | background + poll ≤4min = 0.1× vs 1.25× (12.5×) | 🔧 INC-0 (regla) |
| A3 | Kill-don't-idle | hueco final → morir; rehidratar ~500 tok | ✅ máquina · 🔧 INC-0 (regla) + INC-3 (aviso) |
| A4 | Ruteo por clase de sesión S1/S2/S3 | 2.5× sobre residencia Y output del loop | 🔧 INC-0 (regla) + INC-4 (máquina) |
| A5 | Haiku para TODO bulk-read | hoy 0% medido; `verifier` existe | ✅ agente · 🔧 INC-3 (diente de uso) |
| A6 | Thinking effort como dial | alto solo S1; thinking=output $25/M | 🔧 INC-0 (regla) |
| A7 | Batch API (−50%) slots no-interactivos | runner fuera de Claude Code | 🔧 INC-6 (diferido-declarado) |
| A8 | Ventana promo Sonnet 5 | explotar YA; re-evaluar 2026-09-01 | 🔧 INC-0 (nota) + INC-1 (tabla como data) |

**B · Residencia** — turnos × contexto de Opus (~45% de la factura)
| B9 | Runbook día-a-día: producto-desde-spec = shell/Sonnet, NUNCA Opus (línea 0-modelo, §1.4-2) | **palanca #1 en $/mes, costo 0** | 🔧 INC-0 |
| B10 | Compactación=incidente: hook umbral ~120k → checkpoint + /clear | 3 medidas/incremento → 0 | 🔧 INC-3 |
| B11 | Verbos compuestos: colapsar secuencias Bash repetidas en verbos `meta` de 1 turno | cada turno ahorrado = ctx×0.1× + output | 🔧 INC-3 (audit) |
| B12 | Batching de tool-calls por turno (independientes en paralelo) | menos turnos = menos hits | ✅ disciplina · 📏 KPI INC-1 |
| B13 | Slots headless (`claude -p`): residencia del orquestador durante el slot = $0 | | 🔧 INC-6 |

**C · Contexto** — solo lo necesario, y chico
| C14 | Abstract-first vía grafo (AST, Fase 1 SOTA) como respuesta DEFAULT | mata el churn `server.py`×20 | ✅ grafo · 🔧 INC-3 (default+nudge) |
| C15 | Diente anti-relectura: 3ª lectura del mismo archivo → nudge "grafo/verifier" + KPI churn | 156 re-lecturas extra medidas | 🔧 INC-3 |
| C16 | Abstracts de DOCS + `meta doc slice <doc> <§>` (docs_manifest: abstract 2 líneas + mapa §) | mata "leí el ROADMAP entero ≈30k tok" | 🔧 INC-3 |
| C17 | Archivos chicos con dientes: (a) ✅ gate `quality` (nuevos ~800+); (b) budget de tamaño en slot manifest (`delegation.py` rechaza veredicto que lo viole); (c) opcional hook PreToolUse Write (solo si a+b no alcanzan) | pagan doble: menos tokens por lectura + abstracts útiles | 🔧 INC-3 (b; c diferido) |
| C18 | Salida de gates = 1 línea + artefacto (extender `VEREDICTO` a wrappers gradle/npm) | stdout verboso infla todos los turnos | 🔧 INC-3 |
| C19 | Presupuesto del prefijo fijo: STATE ≤45 ✅ · podar MEMORY.md a punteros (M6) · candidato budget CLAUDE.md | viaja en CADA turno de CADA sesión | 🔧 INC-3 |
| C20 | Higiene de prefijo (no editar CLAUDE.md/agents mid-sesión) | evita invalidación de cache | 🔧 INC-0 (regla) |

**D · Delegación segura** — sin perder potencia
| D21 | `iteration_gate` (<15s: compile+static+tests afectados) vs `acceptance_gate` (1× al final) en el slot manifest; `delegation.py` valida ambos | mata el slot de 79 min | 🔧 INC-2 |
| D22 | `stop_proof` hermético (confía en pin de clon limpio si el toolchain local driftea) + `tools/toolchain.sh` (asegura JDK 21, exporta JAVA_HOME desde el gate) | mata la clase de incidente más cara medida (sesión entera perdida) | 🔧 INC-2 |
| D23 | Ley de tamaño de slot: ≤~30 min wall + budget de tokens declarado (`cost_class` PWF ✅); telemetría compara post-hoc | | 🔧 INC-2 |
| D24 | Plan-como-data + ejecutor Sonnet (S2) + escalación estructurada | el 2.5× sobre el grueso de los turnos | 🔧 INC-4 |
| D25 | Selección de tests por dep-graph (blast-radius → tests afectados) | iteration_gate más rápido | 🔧 INC-2 (mínimo) / INC-4 (pleno) |
| D26 | Dial draft default en loop interno (41.7s vs 98s ✅); harden solo al cierre | | 🔧 INC-0 (regla) |
| D27 | Vehículo sweet-spot para runs medidos (helpdesk 5 ent., no snipeit 19) | | 🔧 INC-0 (regla) |

**E · Medición** — sin esto, todo lo demás es fe
| E28 | Tabla de precios REAL (5 columnas × modelo, §1.2 como DATA fechada) en `billing.py` + ingesta de tipos de token de cache (OTLP: `cache_read`/`cache_creation`) | el ledger deja de ser ciego | 🔧 INC-1 |
| E29 | Detector de expiraciones (spike de `cache_creation` mid-sesión) y compactaciones (✅ ya se cuentan) | decidibilidad de §2.3 e INC-5 | 🔧 INC-1 |
| E30 | Bloque de costo por incremento en `meta outcome`: $ total · share por tier · expiraciones · compactaciones · churn · % delegado · tools/turno | "worth it" decidible, no narrado | 🔧 INC-1 |

---

## §4 · EL PLAN FIJO — N=7 incrementos, orden INMUTABLE (no re-decidir)

> **Reglas de ejecución (fijas):** un incremento por ciclo, en este orden. Cada uno abre su work-doc con el
> slug EXACTO de abajo (`meta increment open <SLUG>`). La sesión que lo ejecute lee SOLO §2 + su fila de acá.
> Los slugs, alcances, dientes y criterios de cierre están CONGELADOS en este doc; si la realidad obliga a
> desviarse, el desvío se declara en el work-doc del INC (residual honesto, I-13) — no se re-planifica acá.
> INC-5 e INC-6 tienen condición de N/A PRE-DECIDIDA: si no disparan, se cierran como N/A-por-medición sin culpa.

| # | Slug | Nivel | Tamaño | Depende de |
| --- | --- | --- | --- | --- |
| 0 | `COST-RUNBOOK` | meta (docs+CLAUDE.md, 0 código) | XS | — |
| 1 | `PRICING-LEDGER` | meta (columna) | S | — |
| 2 | `HARNESS-FAST-GATE` | meta (columna) + cierre FSK diferido | S | — |
| 3 | `CONTEXT-LEAN-TEETH` | meta (columna) | S–M | INC-1 (KPIs) |
| 4 | `PLAN-EXECUTE-SPLIT` | meta (columna) | M | INC-1 + INC-2 |
| 5 | `CACHE-SHAPE` | meta (sondeo+hooks) | XS–S | **condicional a INC-1** |
| 6 | `HEADLESS-SLOTS` | meta (columna) | S | **condicional a INC-4** |

### INC-0 · `COST-RUNBOOK` — las reglas que ahorran desde mañana (0 código)
- **Entregable:** bloque "Runbook de costos (ADR-021)" en `CLAUDE.md` (regla de fase viva) con: (1) tabla de
  ruteo por clase de tarea → sesión/modelo (§2.2, incluye día-a-día = shell/Sonnet NUNCA Opus); (2) kill-don't-idle
  + compactación=incidente; (3) keep-warm en huecos internos; (4) thinking dial; (5) higiene de prefijo;
  (6) draft default + harden al cierre; (7) vehículo sweet-spot para runs medidos; (8) puntero a §2.3 (TTL) y
  a esta biblia. Además: poda de MEMORY.md a punteros si hay solape (regla M6).
- **Diente:** ninguno propio (reglas); las mide INC-1. **Cierre:** CLAUDE.md actualizado + `meta check` verde.

### INC-1 · `PRICING-LEDGER` — que el costo sea un HECHO, no una estimación ciega
- **Entregable:** (a) `billing.py`: modelo de pricing de 2 números → **5 columnas por modelo** (§1.2 como DATA
  fechada, con vencimiento de la promo Sonnet anotado); (b) ingesta de tipos de token de cache
  (`cache_read`/`cache_creation`, telemetría OTLP de Claude Code) al ledger; (c) detector de **expiraciones**
  (spike de `cache_creation` a mitad de sesión) sumado al de compactaciones existente; (d) bloque de costo
  por incremento en `meta outcome` (E30). Multi-archivo (regla 2026-06-25), inglés (ADR-017).
- **Diente:** tests two-sided en la suite (ledger sintético con tokens conocidos → precio EXACTO; entrada de
  cache mal tipada → rechazo). Observador, no gate duro (como `--overlap`).
- **Cierre:** `meta outcome` muestra el bloque de costo con la tabla real; suite verde; baseline del
  incremento DELEG-PAYOFF re-preciado con las 5 columnas (el número que las demás fases deben batir).

### INC-2 · `HARNESS-FAST-GATE` — slots cortos y verificación hermética (los 2 fixes ya destilados)
- **Entregable:** (a) slot manifest schema += `iteration_gate_cmd` (rápido, cada retry; presupuesto declarado
  ≤15s) y `acceptance_gate_cmd` (pesado, 1× al final) — `delegation.py` RECHAZA manifests sin ambos; el
  veredicto exige acceptance verde; (b) `stop_proof` HERMÉTICO: confía en el veredicto pineado del clon limpio
  cuando el toolchain local no puede re-verificar; no re-corre infra pesada al cierre de turno; (c)
  `tools/toolchain.sh`: asegura JDK 21 cacheado y exporta `JAVA_HOME` desde el gate (mata la clase JDK-vanish);
  (d) ley de tamaño de slot (D23); (e) selección mínima de tests por blast-radius (D25).
- **Bonus obligatorio:** des-diferir el cierre formal de `FSK-MUTABLE-WHEN` (re-pin no-adoptantes,
  `ci --rederive --all-products` == pin 4/4) — (c) garantiza el JDK.
- **Diente:** two-sided — manifest sin `iteration_gate_cmd` → rojo; sabotaje del toolchain local con pin
  limpio válido → `stop_proof` NO falso-rojo. **Cierre:** un slot real corrido con iteración <15s + re-pin 4/4.

### INC-3 · `CONTEXT-LEAN-TEETH` — contexto chico con dientes (ataca el ~45%)
- **Entregable:** (a) nudge anti-relectura (PostToolUse: 3ª lectura del mismo archivo en la sesión → aviso
  "grafo/verifier"; C15); (b) abstracts de docs + `meta doc slice` (C16); (c) budget de tamaño de archivo en el
  slot manifest, validado por `delegation.py` al veredicto (C17b); (d) wrappers de gate con salida 1-línea +
  artefacto (C18); (e) hook de umbral de contexto (~120k) → aviso `meta checkpoint` + /clear (B10);
  (f) auditoría de secuencias Bash repetidas → 1–3 verbos compuestos nuevos (B11).
- **Diente:** two-sided en suite para (c); los demás son nudges medidos por los KPIs de INC-1 (churn,
  compactaciones). **Cierre:** un incremento posterior medido con churn <20 y compactaciones 0.

### INC-4 · `PLAN-EXECUTE-SPLIT` — el 2.5× sobre el grueso de los turnos
- **Entregable:** (a) `.gen/plan.json`: WorkOrders ordenados (contrato tipado + ambos gates + radio + deps +
  plan de commits; reusa el vocabulario PWF ya validado); (b) `meta plan check|next|status` — validador
  two-sided (slot sin gate → rojo; DAG acíclico; diferidos declarados); (c) protocolo de escalación
  `.gen/escalations/*.json` (slot, fallo, intentos, hipótesis) que S3 lee; (d) runbook S2 operativo
  (`claude --model sonnet --agent orchestrator` ejecuta el plan mecánicamente).
- **Diente:** `meta plan check` como gate nuevo de `meta check`. **Cierre:** UN incremento real ejecutado vía
  plan con S1/S2/S3 y **opus-share medido < 50%** (baseline 89%) en su bloque `meta outcome`.

### INC-5 · `CACHE-SHAPE` — condicional (la decisión YA está tomada; solo se mide el trigger)
- **Trigger (pre-decidido):** el bloque de costo de INC-1, medido sobre ≥2 incrementos post-INC-3, muestra
  churn de cache (expiraciones+compactaciones) **>10% del gasto**. Si NO → cerrar como **N/A-por-medición**
  (las 3 cartas de §2.3 bastaron); NO re-abrir el debate.
- **Entregable si dispara:** (a) sondeo del knob TTL en Claude Code (docs/changelog/env); (b) si no existe,
  evaluación del camino proxy (rewrite de `cache_control` a `ttl:"1h"` + beta header) con criterio GO/NO-GO
  fijo: GO solo si churn >10% SOSTENIDO y keep-warm insuficiente; (c) formalizar keep-warm como skill/patrón.

### INC-6 · `HEADLESS-SLOTS` — condicional-final (residencia $0 durante slots)
- **Trigger (pre-decidido):** tras INC-4 medido, los slots delegados siguen costando residencia del
  orquestador ≥10% del incremento. Si NO → **N/A-por-medición**.
- **Entregable si dispara:** `meta slot run` (headless `claude -p --model sonnet` con el manifest; veredicto a
  archivo; la sesión solo sondea) + batch API (−50%) como diferido-declarado hasta medir volumen.

---

## §5 · PARA QUÉ — KPIs: cuándo "llegamos" (decidable en `meta outcome`, no narrado)
| KPI | Baseline (2026-07-02) | Target |
| --- | --- | --- |
| Share de Opus por incremento | **89%** | **≤35%** |
| Compactaciones por incremento | 3 | **0** |
| Re-lecturas extra por incremento | 156 | <20 |
| Expiraciones de cache | sin medir (INC-1) | <2/hora de sesión |
| $ por incremento (misma clase) | lo fija INC-1 re-preciando DELEG-PAYOFF | **−60%** |
| Día-a-día (producto desde spec) | sesión Opus ~$86 | **sin sesión Opus** (~10×) |
**"Llegamos"** = 2 incrementos consecutivos post-INC-4 cumpliendo TODOS los KPIs no-condicionales.
La dirección se declara COMPLETA en ese momento (aunque INC-5/6 cierren N/A).

## §6 · Qué NO hacer (anti-palancas, con evidencia — tan fijas como el plan)
1. **No multi-agente paralelo para codegen secuencial** (~15× tokens medido; sin paralelismo real pierde).
2. **No bajar S1/diseño ni la COLUMNA a Sonnet**: construir-lo-equivocado es el fallo más caro (lección
   Snipe-IT: 17 incrementos ADOPT); el trust-chain se escribe con ojos (SELF-IMPROVEMENT §3).
3. **No `agent` global en settings** (ADR-020 (a)) · **no roles por dominio** (ADR-020 (c)).
4. **No acortar la verificación para ahorrar**: el pin del clon limpio ES lo que hace seguro delegar barato.
5. **No obsesionarse con el TTL** más allá de su 5–15%: las palancas del 85% son ruteo+contexto+turnos.
6. **No sobre-hookear** (C17c queda diferido salvo que a+b midan insuficiente): la fricción también es costo.

## §7 · Punteros (para profundidad, NO para re-decidir)
- **ADR-021** (`decisions/021-economia-opus-marginal.md`) — la decisión inmutable que este doc detalla.
- `work/DELEG-PAYOFF-MEASURE-INCREMENT.md` — las mediciones crudas + el modelo de costo destilado.
- ADR-017 (routing como dato) · ADR-020 (roles cerrados, delegación activada) · ADR-019 (memoria: podar antes
  de agregar) · `reference/OBSERVABILITY-METRICS.md` (el split) · `reference/PRIMITIVES.md` (filosofía).

## Fases (de ESTE incremento de dirección)
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Biblia auto-contenida (este doc): evidencia + doctrina + catálogo + plan FIJO N=7 + KPIs | ✅ |
| 2 | ADR-021 (decisión inmutable y citable) | ✅ |
| 3 | Punteros: STATE «Ahora» + ROADMAP → esta biblia | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. Este doc existe, auto-contenido (una sesión sin contexto puede ejecutar INC-0..INC-6 sin re-diseñar). ✅
2. `decisions/021-economia-opus-marginal.md` aprobado, con la decisión (a)–(d). ✅
3. STATE «Ahora» (≤45) y ROADMAP apuntan acá; `meta check` verde. ✅
4. El plan es FIJO: slugs, orden, triggers de N/A y KPIs congelados en §4–§5. ✅
