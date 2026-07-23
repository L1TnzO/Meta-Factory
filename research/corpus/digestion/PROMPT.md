# PROMPT — digestión por lotes SMS v2 (contrato de delegación, §7.4 — el destino del corpus)

Eres un digestor de papers para alimentar la MEMORIA de un prototipo (Meta-Factory). Cada paper YA fue
INCLUIDO y YA fue extraído: los facetados tipados (`operaciones`, `representacion`, `F`, `evidencia_tipo`)
vienen DADOS en el input y son la VERDAD CONGELADA — los **copias tal cual**, NUNCA los re-inventas
(el validador rechaza cualquier deriva contra la extracción). Tu trabajo NUEVO es la SÍNTESIS: qué
problema ataca, cómo funciona el mecanismo, qué números clave reporta, y —lo más importante— **cómo
aplica a Meta-Factory** (la lente MF). No re-decides membresía; si al leer crees que no debió entrar,
digiérelo igual y anota `RECONSIDERAR` en `notes` — la decisión es humana.

## Entrada
Archivos `d<NN>.input.jsonl` (un chunk = un archivo): un registro JSON por línea con
`key, cita, operaciones, representacion, F, evidencia_tipo, plan_estado, pdf`. El PDF existe SIEMPRE.

**Protocolo de lectura (desde `research/`, presupuesto por paper ~45k chars):**
1. `pdftotext corpus/pdf/<key>.pdf - | head -c 30000` — intro, arquitectura, mecanismo.
2. Si faltan números: `pdftotext corpus/pdf/<key>.pdf - | grep -in -B2 -A6 -E "ablat|benchmark|token|cost|latenc|baseline|Table" | head -c 12000`.
3. Los facetados del input orientan la lectura; los números y la prosa se llenan CONTRA EL PDF.

## Salida (por chunk, OBLIGATORIA antes de abrir el siguiente input)
Escribe `d<NN>.verdict.jsonl` JUNTO al input (un objeto JSON por línea, con `json.dumps`, nunca a mano).
Un objeto por paper, con EXACTAMENTE estas claves:

| Campo | Contenido | Regla dura (el validador rechaza si la violas) |
| --- | --- | --- |
| `key` | la del input | == input |
| `cita` | la del input, tal cual | == extracción (copia) |
| `problema` | 1–3 frases: qué vacío/problema de memoria ataca | prosa ≥20 chars |
| `mecanismo` | cómo funciona el mecanismo de memoria (write/consolidate/retrieve/forget · representación) | prosa ≥30 chars |
| `operaciones` | lista JSON de tokens, **copiada del input** | set == extracción |
| `representacion` | lista JSON de tokens, **copiada del input** | set == extracción |
| `evaluacion` | benchmarks + método de evaluación en prosa | prosa ≥20 chars |
| `numeros_clave` | números clave del PDF (deltas de ablation, % éxito, tokens, latencia) o `"NINGUNO"` | si `evidencia_tipo` ∈ {ABLATION, BENCHMARK-E2E, MEDICION-COSTO} ⇒ NO puede ser `NINGUNO` (cita un número real) |
| `F` | lista JSON de facetas, **copiada del input** | set == extracción |
| `mf_aplicabilidad` | lista JSON de `{ancla, postura, nota}` — la LENTE MF (≥1) | ver abajo |
| `notes` | ancla de evidencia (sección/página/tabla) de lo no obvio + `RECONSIDERAR` si dudas | prosa ≥15 chars |

### `mf_aplicabilidad` — la lente Meta-Factory (el aporte central de la digestión)
Lista de ≥1 objeto `{"ancla": …, "postura": …, "nota": …}`. `nota` = 1 frase justificando, con ancla al PDF.

- **`ancla`** (vocabulario CERRADO — necesidad MF que el paper toca):
  `G-M1` (disparador de escritura) · `G-M2` (retrieval medido) · `TIER-DOCS` (docs=verdad, narrativa tipada) ·
  `TIER-INDICE` (índice derivado=caché) · `FIDELIDAD` (procedencia/staleness/poisoning) ·
  `COSTURAS` (fuente-única-por-hecho / multi-almacén) · `NEGATIVO` (conocimiento negativo) ·
  `CONSOLIDACION` (promoción de gotchas a recetas durables) · `PLAN-ESTADO` (estado-de-plan como memoria) ·
  `COSTO` (economía de contexto: tokens/caché/latencia/compaction).
- **`postura`** (vocabulario CERRADO — qué le hace el paper a la decisión MF actual):
  `CONFIRMA` (la evidencia externa apoya la decisión MF) · `REFUTA` (la desafía — p. ej. alguien MIDIÓ que
  embeddings baten a grep, contra ADR-019) · `EXTIENDE` (ofrece un mecanismo/patrón que MF podría adoptar) ·
  `NEUTRAL` (contexto relevante sin fuerza direccional).
- **Obligaciones (el validador las exige):** si `F` contiene `DOCS-VERSIONADO` ⇒ debe haber una entrada con
  ancla `TIER-DOCS`. Si `F` contiene `NEGATIVO` ⇒ ancla `NEGATIVO`. Si `plan_estado=SI` ⇒ ancla `PLAN-ESTADO`.
  (La postura es libre; solo el ancla es obligatoria — son los diferenciadores MF de por qué el paper se digiere.)

## Disciplina de proceso
- Chunks EN ORDEN; escribe cada `d<NN>.verdict.jsonl` ANTES de abrir el siguiente input (checkpoint).
- No leas el protocolo ni otros archivos del repo: este prompt es autosuficiente.
- `pdftotext` SIEMPRE dentro de tu spawn, con los límites de arriba (jamás el PDF entero sin `head -c`).
- Al terminar reporta SOLO: chunks completados · nº papers · nº con `RECONSIDERAR` · nº `REFUTA` en
  `mf_aplicabilidad` (los que desafían una decisión MF — señal de alto valor). NUNCA pegues texto de PDFs.
