# HANDOFF — Cierre del SMS v2: colas, corpus, gris y ESCRITURA (2026-07-24, fase ABIERTA)

> Para retomar con amnesia total: este doc + §9 del `SMS-V2-PROTOCOL.md` (la ley congelada de esta fase) +
> bitácora §8 (single-source de números de las fases previas). Ante duda, `git log --oneline -- research/`.

## 0. Por qué existe esta fase (el porqué, no el qué)

El SMS v2 no es un trámite de curso: es **la base de evidencia de dos cosas a la vez**.

1. **Académico** — el `Anteproyecto_ID.tex` (ICC760, UFRO) apoya hoy su §2.4 «Evidencia del mapeo
   sistemático» en el **SMS v1: 27 estudios, 3 RQs, anclado en debugging/APR**. Ese anclaje ya no describe
   el proyecto: el proyecto es un agente de **larga vida con memoria de proyecto**. El v2 re-ancla el
   mapeo (PCC §2) y lo lleva a **1.069 registros cribados → 487 incluidos → 422 digeridos con texto
   completo**, con 7 RQs. La escritura del v2 es lo que convierte ese trabajo en evidencia citable.
2. **Ingenieril** — cada RQ está mapeada 1:1 a una necesidad REAL y declarada de Meta-Factory (§2/§3):
   G-M1 (trigger de escritura), **G-M2 (retrieval medido)**, tiers docs/índice, fidelidad/anti-drift,
   economía de contexto, costuras multi-almacén, conocimiento negativo, consolidación, estado-de-plan.
   El digest (`corpus/digestion/digest.jsonl`) alimenta la memoria del prototipo y —lo importante— puede
   **refutar** decisiones congeladas: `REFUTA` 64, y **más de un tercio se concentra en `G-M2`**, la
   decisión de ADR-019 (retrieval por grep, embeddings descartados-por-medición). El corpus está diciendo
   algo incómodo y el SMS tiene que decirlo.

Dicho al revés: si esta fase no se escribe, el trabajo de cinco fases de máquina (búsqueda → cribado →
snowball → extracción → digestión, ~20M tokens medidos) no le llega a ningún humano ni a ninguna decisión.

## 1. Estado de entrada (verificado 2026-07-24T16:0xZ)

- Fases de máquina COMPLETAS: búsqueda (1.069) · cribado (1.069/1.069) · snowball (968) · extracción
  (422/422 pdf-ok) · digestión (422/422, gate 71/71, `digest.jsonl` 422 registros).
- **La red FUNCIONA en esta sesión** (`openalex:200 · arxiv:200 · anthropic:200`) → cae el residual §8 que
  difería el rescate de PDFs y la cosecha gris a «la máquina local».
- **LaTeX disponible**: TinyTeX instalado en `~/.TinyTeX` (sin sudo) + IEEEtran/babel-spanish verificados
  con un compilado de prueba. Antes NO había toolchain: el paper se puede compilar aquí mismo.

## 2. Qué falta (todo lo que queda del SMS v2)

| # | Fase | Qué es | Diente |
| --- | --- | --- | --- |
| **A** | **SPI — segunda pasada independiente** (§9.1) | 534 filas de cola en 4 tipos (verificación · adjudicación · calidad · identidad); mide acuerdo + κ y reduce el borde humano a los CONFLICTOS | `verify_spi_verdicts.py` (ley `closure_law.py`) + test de ceguera |
| **B** | **Cierre de corpus** (§9.3) | rescate de los 65 `pdf_status=missing` con red; extracción+digestión de lo rescatado y de los flips de A, en chunks NUEVOS (`e72+`, `d72+`) | gates congelados §7.6/§7.4 |
| **C** | **Literatura gris RQ7** (§9.4) | RQ7 hoy tiene **cero** registros; snapshot inmutable de docs de Anthropic/OpenAI/DeepMind + digest con la lente MF | manifest con sha256 verificado |
| **D** | **PLAN-ESTADO** | promover la faceta (evidencia `plan_estado=SI` = 70, 14× el umbral ≥5) por derivación, sin re-etiquetar 422 filas | derivada, no anotada a mano |
| **E** | **Escritura del SMS v2** (§9.5) | `sms-v2/` — claims-as-code + bib generada del corpus + `.tex` + PDF | `verify_sms_claims.py` (5 dientes) |
| **F** | **Propagación** (§9.6) | `Anteproyecto_ID.tex` §2.4 + Anexo pasan de 27 estudios a la evidencia v2 | números re-derivados |

## 3. Decisiones de diseño de esta sesión (las que hay que respetar)

1. **«Lo humano» NO se falsifica.** Un agente no puede *ser* la revisora. Lo que sí puede —y es
   metodológicamente superior a una cola parada— es ser un **segundo revisor independiente y ciego**:
   produce el acuerdo/κ que el protocolo declaraba faltante y deja como cola humana REAL sólo los
   conflictos. La etiqueta «dos revisores-modelo, no dos humanos» es obligatoria en el paper (§9.1).
2. **La prosa no tiene compilador, pero los números sí.** Ninguna cifra del paper se escribe a mano: viven
   en `claims.yml`, se re-derivan del corpus y entran al `.tex` como macros (§9.5). Una cita alucinada es
   imposible por construcción porque el `.bib` se genera del corpus. Esto satisface por máquina la regla
   no negociable de la guía del informe final («nunca inventes datos, métricas ni citas»).
3. **Nada se re-escribe, todo se añade.** Correcciones de corpus → chunks nuevos; filas degradadas →
   registradas, no borradas. La procedencia ES el corpus.

## 4. Orden de ejecución y por qué

`B(rescate, red, en background)` ‖ `A(toolkit → olas SPI)` → `B(extracción/digestión de lo rescatado)` →
`C(gris)` → `D` → `E(claims → tex → pdf)` → `F`.

El rescate de PDFs es I/O de red sin modelo → va en background mientras corren las olas de la SPI
(keep-warm, runbook (b)). La escritura es lo ÚLTIMO porque sus números son derivados: cualquier flip de A o
paper rescatado en B cambia los denominadores, y con claims-as-code eso se re-emite solo.

## 5. Ciclo de ola (probado 25× en digestión, 24× en extracción — no reinventar)

manifest `.gen/active_slot.json` (`allow_globs` = los verdicts de la ola, gate de aceptación `--require`) →
`generator` (Sonnet; PDFs vía `pdftotext … | head -c`, NUNCA al hilo principal; **checkpoint con gate por
chunk ANTES de abrir el siguiente**) → verificar por bloqueo (gate `--require` + `slot_footprint --live`) →
commit → `clear_slot`. Ola óptima medida: 2–3 chunks. Un corte de sesión cuesta, como máximo, un chunk.
