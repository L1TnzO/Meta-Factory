<!-- meta:doc sha=bdc4f7e42634b57507cca23b2fbf1519b18cceab updated=2026-07-10T22:27Z -->
<!-- meta:doc sha=PENDING updated=2026-07-10T22:26Z -->
# ADR-025 — Adopción de un producto evaluable externo como producto de fábrica: `eval_floor` (generaliza ADR-024) + thaw de ASF para ReqCouncil

| Campo | Valor |
| --- | --- |
| Estado | Propuesto |
| Fecha | 2026-07-10T22:26Z |
| Decide | el ingeniero (2026-07-10, «tengo para ASF `dataset_agent_re` = el agent_re pero evaluable; hay que meter todo y ponerlo como product de ASF»); analiza, diseña y propone el orquestador |
| Concreta / revisa | ADR-024 §46 («F1/ASF hereda el modo» — este ADR le da la forma concreta para un PRODUCTO entero) · ADR-023 §3 (freeze-con-pin del codegen: este ADR agrega override+perfil, NO alimenta templates) · ADR-023 §4 (el moat = artefacto PINEADO re-verificado) · ADR-021 (ruteo por sesión: adopción = S2/Sonnet; el diseño y la ley del gate = S1/Opus) · ADR-016 (gobierno por nivel: descompone en incremento META + incremento ASF) |
| Referencia | `~/University/Integración/APP/dataset_agent_re` @ `89ad45b` (ReqCouncil, el producto adoptado) · `factories/full-stack-kotlin` (precedente `design_floor` + override pineado de ADR-024) · `reference/ASF-PROVENANCE.md` (precedente de pin a un SHA upstream) |

## Contexto (medido, no narrado)
1. **`dataset_agent_re` = ReqCouncil: el producto que ASF fue chartereada a producir, ya construido a mano y
   ya EVALUABLE.** Sistema multi-agente de elicitación de requisitos (6 analistas + críticos que deliberan
   hasta consenso, LangGraph, HITL). Entrada: transcripción speaker-tagged. Salida: `RunOutcome` (requisitos
   worst-first + draft + rondas + review). Evaluable por 4 datasets golden (Inter2US, ReqElicitBench,
   WEPGCOMP/+Lugar, RECOVER) y 5 experimentos E0–E4 con gates que BLOQUEAN: `fidelity`≥0.7, `critical_nfr_recall`
   ≥0.9, `cci_band` 0.6–1.6, `judge_agreement`≥0.8, `no_regression` (>2pts drop vs pin).
2. **Ya implementa la disciplina model-nativa de ADR-023 §4, pre-construida.** Corre el council caro (LLM)
   una vez → PINEA los runs (`runs/pinned/`, 182 files, 2.7M) → `python -m reqcouncil eval gates` los
   RE-VERIFICA hermético (zero-LLM, pinned-runs vs `config/thresholds.yml`). Es exactamente
   «re-verificar el artefacto pineado, no re-derivarlo» — el moat de FSK vía `design_floor` + `ci --rederive`
   con `claude` SABOTEADO, ya presente acá bajo otro nombre.
3. **ADR-024 cubre una SUPERFICIE model-nativa, no un PRODUCTO entero.** Dio el mecanismo para un override de
   presentación (`frontend/app.ts` + `design_floor` browser/a11y) sobre un chasis de templates. No cubre
   adoptar un producto COMPLETO evaluable como artefacto pineado verificado por un arnés de eval REAL (métricas
   semánticas contra ground truth), ni cubre un producto SIN chasis de templates debajo.
4. **ASF está REGRESSION-FROZEN** (su `docs/STATE.md`, COUNCIL-360 camino B) y `products/` está VACÍO.
   Descongelar = acto DELIBERADO con motivo escrito + demanda real (decisión del ingeniero). La demanda ES
   ReqCouncil: un agente RE evaluable en uso académico real (UFRO). El ingeniero decidió en esta sesión.
5. **Restricción de datos (medida, no asumida).** `datasets/` = 803M de terceros; `datasets/README.md`:
   «solo evaluación/investigación, citar siempre la fuente; no redistribuir fuera del repo del proyecto»;
   ReqElicitBench **no declara licencia**. El repo Meta-Factory es **PRIVADO** (verificado:
   `L1TnzO/Meta-Factory → PRIVATE`) → un espejo privado del mismo dueño, mismo uso académico, NO es
   redistribución a terceros. Se copian con su NOTICE/citación; guard hacia-adelante: si el repo se hiciera
   público, `datasets/` se excluye.

## Decisión
1. **Thaw de ASF, ADITIVO.** Se levanta el regression-freeze SÓLO para AGREGAR un producto adoptado; las
   estaciones y el (inexistente) producto-template frozen no se re-derivan → sin regresión. **Motivo escrito**
   (el que la gobernanza exige): *superar el demo flaco (el `agent_re` esqueleto de F1) con el producto RE
   real y evaluable; demanda = uso académico real en curso.* No toca `codegen/scaffold/blueprint.py` ni el
   codegen congelado → **sin waiver de `codegen_freeze`**.
2. **Adopción full-copy como producto de ASF.** ReqCouncil se copia ENTERO a
   `factories/agent-systems-factory/products/reqcouncil/` (`reqcouncil/` código + `config/` + `tests/` +
   `runs/pinned/` + `docs/` + `datasets/` + NOTICE/licencias). Patrón «copiado-no-emitido» de ADR-024 §2,
   **generalizado** de «override de superficie» a «producto entero adoptado». El árbol del producto es el pin.
3. **`eval_floor` = generalización de `design_floor` (ADR-024 §3).** Un producto declara su PERFIL DE
   VERIFICACIÓN EXTERNO: un comando de re-verificación HERMÉTICO (`python -m reqcouncil eval gates`) +
   evidencia pineada (`runs/pinned/`) + umbrales (`config/thresholds.yml`). La línea de fábrica lo corre
   OPT-IN. `design_floor` (browser) y `eval_floor` (métricas de eval) son dos instancias del MISMO concepto:
   re-verificar evidencia pineada contra un piso, 0-modelo. El mecanismo **nombra NINGÚN dominio** (lo protege
   el gate `generality`): el producto TRAE su comando y sus umbrales como DATO (ADR-012).
4. **Verificar-no-re-derivar es el pin (ADR-023 §4).** Para el producto adoptado, `ci`/`meta check`
   RE-VERIFICA (`eval gates`, pyyaml-only, SIN datasets ni LLM ni langgraph), NO re-corre el council. Correr el
   council (langgraph + LLM) es acto DELIBERADO, out-of-band — es la re-generación/mejora, no la verificación.
5. **Provenance + drift.** La copia es un snapshot PINEADO a upstream `89ad45b` (`products/reqcouncil/PROVENANCE.md`,
   precedente `ASF-PROVENANCE.md`). `dataset_agent_re` sigue siendo el **dev upstream**; re-sync = acto
   deliberado (re-copy + re-pin de métricas). Los `datasets/` llevan un **manifest** (checksums + fuente) trackeado
   → durables y re-hidratables aunque el working-tree se limpie; los 803M dejan de depender del dir externo.
6. **Modo MEJORA (el payoff — fase 2, tras la adopción).** Con el producto in-house + `eval_floor` como
   TRINQUETE (`no_regression` contra ground truth REAL), cada mejora es un slot model-nativo gateado: el
   `generator` (Sonnet) escribe la mejora; el gate = correr el eval real vs el piso pineado + `no_regression`;
   el veredicto = métricas dentro de banda o mejor. Ese es el valor que la adopción DESBLOQUEA — y el moat que
   el council pidió: re-derivabilidad + escape-rate sobre datos reales, no velocidad día-1.
7. **Diente two-sided (como ADR-024 §5).** Producto opt-in sin `runs/pinned` o cuyo `eval_floor` no corre →
   ROJO; producto sin opt-in que igual corre `eval_floor` → error de config → ROJO. La adopción no puede
   romper en silencio los pins existentes de otras fábricas.

## Consecuencias
- **ASF cambia de naturaleza (explícito, sin sobre-vender):** deja de ser «una fábrica que genera un agente RE
  flaco» y pasa a ser **el hogar eval-gateado de un producto RE real que se MEJORA bajo trinquete**. ASF no
  «genera» ReqCouncil — lo ADOPTA y lo CUSTODIA bajo un piso de eval real y re-verificable. Ese ES el valor de
  fábrica en el paradigma model-nativo (spec + perfil de verificación + memoria + re-verificabilidad del pin).
- **Descomposición en incrementos (por nivel, ADR-016):**
  - **META substrate** (general, TRUST-CHAIN): máquina de adopción de producto-entero + `eval_floor` pluggable
    (perfil de verificación externo declarado como DATO) + el gate wired a la línea de fábrica. Opus diseña la
    LEY del gate con ojos propios; Sonnet ejecuta el resto. Protegido por `generality` (no nombra dominio).
  - **ASF adoption** (fábrica): thaw + copy físico + `PROVENANCE.md` @89ad45b + manifest de datasets + wiring de
    spec/station para declarar el producto y su `eval_floor` + update de `docs/STATE.md`. Ejecutable por Sonnet
    S2 (mayormente mecánico); el motivo escrito lo firma el ingeniero (§Decisión 1).
  - **Diferido → ADR-026 `COMMUNITY-FRESHNESS` (G1):** los pins de comunidad que trae el producto (langgraph,
    SDK DeepSeek, psycopg, pgvector; `requirements.txt` congelado 2026-07-06) son supply-chain del CEREBRO. Su
    política (frescura verificada con MCP/context7, sólo-S1) entra CON el incremento de mejora/re-pin (fase 2),
    NO antes — no se escribe máquina especulativa. El día-a-día del árbol meta queda limpio: `eval_floor` es
    pyyaml-only, langgraph sólo se necesita para re-generar el pin.
- **Costo (medido):** adoptar ≈ 5.5M en git (código + `runs/pinned`) + 803M de datasets on-disk (privado, OK).
  El único costo real recurrente es el clean-clone CI del meta; mitigable en ejecución (sparse-checkout / LFS)
  porque `eval_floor` provablemente no lee `datasets/`. Re-verificar = 0-modelo. Mejorar = tokens-de-slot bajo
  gate (fase 2).
- **El codegen de templates sigue CONGELADO (ADR-023 §3 intacto).** Este ADR agrega un mecanismo de override
  (copiar en vez de emitir) + crece el PERFIL DE VERIFICACIÓN (`eval_floor` opt-in) — ambos son la parte VIVA
  de una fábrica bajo ADR-023 §1, no alimentan templates.
