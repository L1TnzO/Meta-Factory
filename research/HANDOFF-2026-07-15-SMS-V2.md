# HANDOFF — Sesión SMS v2 (2026-07-15)

> Para retomar con amnesia total: este doc + `SMS-V2-PROTOCOL.md` (la autoridad metodológica) bastan.
> Todo lo afirmado aquí tiene commit; ante duda, `git log --oneline -- research/` es la verdad.

## 0. Qué es esto

Segunda iteración del mapeo sistemático (SMS) sobre **memoria persistente en agentes LLM para ingeniería de software**, re-anclada a las necesidades de Meta-Factory. El v1 (`sms.tex`, curso ICC760, 27 papers, mayo 2026) queda sin autoridad: la ingeniera lo declaró no-confiable y todo lo reutilizado de él fue demostrado con datos o botado. El destino del corpus es doble: (a) el SMS v2 como documento, (b) alimentar la memoria del prototipo Meta-Factory (digests tipados).

## 1. Decisiones de la ingeniera en esta sesión (vinculantes)

1. **Ancla**: núcleo Meta-Factory (memoria de proyecto en agentes SE de larga vida) + debugging como subcaso, no como eje.
2. **Fuentes**: OpenAlex + Lens.org + arXiv nativo (reemplazan Scopus/WoS/IEEE/Scholar/S2) + literatura gris de Anthropic/OpenAI/GDM.
3. **Ubicación**: todo en `research/` del repo, committeado (ADR-010).
4. **Tubería de cosecha incluida** (scripts stdlib, en `research/harvest/`).
5. **Mandato anti-autoridad-v1** (turno 2026-07-15 tarde): «asume que v1 no es el mejor trabajo; si reutilizas algo, DEMUESTRA por qué». Ejecutado en v2.2 (§5 abajo).
6. La rúbrica de cribado se estresó contra abstracts reales a pedido de ella → dimensión F añadida (§7 abajo).

## 2. Estado del corpus (CERRADO — fase de búsqueda completa)

- **1.069 trabajos únicos** en `corpus/merged/corpus.jsonl` (+ `corpus.csv` vista plana).
- Procedencia (run 3): OpenAlex core 453 + arXiv core 191 + OpenAlex general (Q2) 1.291 + arXiv general 337 + Lens core 321 + Lens general 948 = 3.541 filas → dedup DOI→arXiv→título.
- **917/1.069 (86%) en ≥2 fuentes** — validación cruzada fuerte de la cadena.
- **PDFs: 598 en disco (55%, 2,9 GB)** en `corpus/pdf/` (gitignored); índice = `corpus/pdf_manifest.csv` (committeado, sha256 por archivo). Resto: 271 landings no-PDF, 98 HTTP bloqueados (editoriales), 91 sin OA (coherente CE-4), 11 transitorios. **Política: recuperar a mano SOLO los que pasen el cribado.**
- `corpus/pdf/` guarda ~330 PDFs huérfanos de claves de runs previos (re-derivables, inocuos; limpiar si molestan).
- Conteos de cadena en OpenAlex (2022+): réplica v1 = 143 · core v2 = 429→453 (v2.1). El ×3 fue la apertura del vocabulario nuevo.

## 3. La cadena (v2.2, CONGELADA) — evolución con evidencia

- **v2.0**: estructura A∧B∧C del v1 + 21 términos nuevos (léxico 2025-26: agent/agentic memory, memory system, context engineering, consolidation, skill library…) + scope 2022+.
- **v2.1** (tras sanidad run-1 9/20, con abstracts verificados): A += `"experience bank"`, `"experience-driven"` (SWE-Exp fallaba A); B += `"LLM-based"` (ExpeRepair fallaba B); **rama Q2** = A-fuerte EN TÍTULO ∧ B, sin C (MIRIX-clase: sistemas de memoria generales sin término SE; CI-2 los admite como transferibles).
- **v2.2** (auditoría anti-v1): drops demostrados `"software testing"` (0 hits) y `"bug fixing"` (0 contribución única) con **prueba de equivalencia** (corpus v2.2 ≡ v2.1, sin re-cosecha). Todos los demás términos retenidos por contribución única MEDIDA (§4.5 del protocolo tiene los números).
- Consultas como DATOS en `harvest/queries/`: `{openalex,arxiv,lens}_core.txt` + `{openalex,arxiv,lens}_general.txt` + `openalex_extended.txt` (variante de sensibilidad, no corrida aún).

## 4. Sanidad — gold set (v1 degradado)

- **Gold set** (12 obras comunidad-validadas, c/u mapeada a una necesidad MF; lista con arXiv ids en `harvest/sanity_check_gold.py`): MemGPT, Voyager, Reflexion, ExpeL, Generative Agents, MemoryBank, HippoRAG, A-Mem, Mem0, AWM, Titans, Sleep-time.
- Medido: **3/12 en corpus** (MemoryBank, A-Mem, Mem0) · **7/12 citados por el corpus** (snowball hacia atrás garantizado) · **2/12 solo-semilla-manual** (Voyager, Generative Agents — su rol por §7.3 igualmente). Si «solo-semilla» crece entre runs → la cadena deriva del campo.
- v1: 14/20 sistemas presentes (línea informativa `--also-v1`, SIN autoridad). Los 6 ausentes (ContextWeaver, Springdrift, SMITH, Mem2Evolve, LMEB, Dual-Cluster) = **hueco de FUENTE** (cero rastro en OpenAlex+arXiv+Lens; origen S2/IEEE o no indexados) — entran como candidatos vía `references.bib` (pendiente, ver §9).

## 5. Auditoría anti-autoridad-v1 (v2.2) — resumen de veredictos

| Herencia v1 | Veredicto | Evidencia |
| --- | --- | --- |
| Términos A/B/C | RETENIDOS (menos 2 drops) | contribución única por término sobre los 1.069 (§4.5 protocolo) |
| Estructura A∧B∧C | RETENIDA | sus partes auditadas + su modo de fallo conocido (excluir sistemas generales) parchado por Q2 |
| Los 27 como estándar de sanidad | BOTADO | reemplazado por gold set §4.6 |
| Los 27 como semillas de snowballing | BOTADO | semillas = incluidos v2 + gold set; los 27 = candidatos bajo CI/CE normales |
| CI/CE v1 | re-derivados uno a uno (tabla §7.5) | CE4-short-papers botado con razón; CE3-gratis heredado coherente con corpus OA |
| RQs | no venían del v1 | derivadas de MEMORY-ARCHITECTURE.md + ADR-019 (y afinadas con la lectura completa) |

## 6. Protocolo — mapa del documento (`SMS-V2-PROTOCOL.md`)

§1 delta v1→v2 · §2 PCC + necesidades MF citadas (G-M1, G-M2, tiers, fidelity, anti-drift, costo, costuras/fuente-única, conocimiento negativo, promoción de gotchas) · §3 RQ1–RQ7 + tabla RQ↔necesidad↔dónde vive en el repo · §4.1 crítica v1 · §4.2 cadena core · §4.3 extendida + promociones v2.1 · §4.4 rama Q2 · §4.5 auditoría de términos · §4.6 gold set + cobertura por necesidad · §5 consultas por fuente (URLs 1-clic con conteos anotados) · §6 literatura gris (tabla de 11 semillas VERIFICADAS de Anthropic/OpenAI/Google + método snapshot + tier 2 opcional) · §7.1 tubería + comando único · §7.2 esquema normalizado · §7.3 snowballing sin v1 · §7.4 digestión al prototipo · §7.5 cribado (CI/CE, rúbrica M/T/E/F, proceso 4 pasos) · §7.6 formulario de extracción (borrador) · §7.5b pendientes · §8 bitácora de runs y decisiones (los residuales honestos viven ahí).

## 7. Cribado — diseñado, calibración PENDIENTE (el paso bloqueante)

- **CI/CE v2.2**: tabla completa en §7.5 con la justificación de cada herencia. CE-5 (nuevo, hallazgo de la revisión de abstracts): depósitos de software Zenodo/GitHub indexados como papers (p. ej. «MemForge v0.5.6») → fuera del corpus, catalogar en `corpus/artifacts.csv`.
- **Rúbrica**: M (mecanismo 0/1/3) · T (transferibilidad a agentes SE de larga vida 0/1/2) · E (evidencia 0/1). Corte inicial: M+T+E ≥ 4 con M≥1; rama Q2 (sin señal SE) exige M=3. **A calibrar.**
- **F (facetas MF, multi-etiqueta, NO corta — prioriza)**: WRITE · RETRIEVAL-MEDIDO · DOCS-VERSIONADO · FIDELIDAD · CONSOLIDACION · COSTO · MULTIAGENTE · SEGURIDAD · NEGATIVO · PROCEDIMENTAL. Razón: M/T/E no distingue memoria-de-chatbot de memoria-gobernada (probado leyendo abstracts: MemPro vs Git-Context-Controller misma nota).
- **Hallazgo pre-cribado (candidato a hallazgo central del SMS)**: conteo de facetas sobre los 1.069 → **WRITE 6 · NEGATIVO 11** (lo que MF más necesita es lo más escaso del campo) vs SEGURIDAD 137 · CONSOLIDACION 185 · FIDELIDAD 239 (regex amplia, podar al revisar).
- **Triage determinista** (reglas como datos en `make_screening_sheet.py`): PRE-IN 468 · GRIS 524 · PRE-OUT 77. No decide; ordena y da denominadores.
- **Hojas listas**: `corpus/screening/screening_full.csv` (1.069, con señales + hints de facetas + columnas M/T/E/F/decision/notes vacías) y `corpus/screening/calibration_sample_50_seed42.csv` (25 con señal SE + 25 rama general).

## 8. Infraestructura (`research/harvest/`)

| Archivo | Qué hace |
| --- | --- |
| `harvest_all.sh` | runner completo; `SKIP_HARVEST=1` reutiliza raw (p. ej. al añadir exports de Lens); corre gold-check al final |
| `openalex_harvest.py` | cursor paging, `--raw` (rama Q2 con doble filtro), `--count-only`, retry 429/5xx con Retry-After, escritura atómica |
| `arxiv_harvest.py` | Atom API, quote_plus (límite URL ~2k — ese fue el HTTP 500), retry 5xx, escritura atómica, 3s ToS |
| `merge_dedup.py` | normaliza+dedup (DOI→arXiv→título), procedencia acumulada, WARNING si un input aporta 0 |
| `download_pdfs.py` | resumible; toda identidad arXiv → mirror export; %PDF magic; manifest sha256; no-ASCII quoted |
| `sanity_check_gold.py` | gold set 12 + `--also-v1` informativo |
| `make_screening_sheet.py` | hoja de cribado: señales transparentes, triage, hints de facetas MF, muestra estratificada |
| `sanity_check_v1.py` | legado, superseded por gold (mantener solo como referencia) |

**Quirks de entorno para la próxima sesión**: el sandbox de Cowork NO alcanza api.openalex.org/arxiv.org (proxy 403 allowlist) → cosechas corren en la máquina de la ingeniera; `web_fetch` no renderiza JSON/XML y limita URLs a ~450 chars; la extensión Chrome estuvo desconectada toda la sesión (si conecta: conteos en vivo y cosecha gris los hace el agente); tras cada commit desde el sandbox quedan locks de git → `rm -f .git/*.lock .git/objects/maintenance.lock` (ya habilitado el permiso de borrado); commits estilo `tipo(SMS-V2): ...` + trailer `Co-Authored-By`.

## 9. CAMINO HACIA ADELANTE (en orden)

1. **[Catalina — BLOQUEANTE] Calibración**: cribar los 50 de `calibration_sample_50_seed42.csv` llenando M/T/E/F/decision (~45-60 min). Observar: ¿anclas ambiguas? ¿facetas que faltan/sobran? ¿el corte ≥4 con M≥1 deja fuera algo valioso? → devolver al agente.
2. **Congelar rúbrica** con lo aprendido (ajustar anclas/umbral/facetas; anotar en §7.5; commit).
3. **Pasada completa** sobre los 1.069: humana, o delegada estilo `evaluator` (ADR-017/027: rúbrica-como-DATA, modelo barato, por lotes) con verificación humana de 10% aleatorio + toda la zona gris del modelo + todo PRE-OUT que quiera incluir. Decisiones quedan en `screening_full.csv` (commit = procedencia de cada exclusión). Durante la pasada: aplicar CE-5 → poblar `corpus/artifacts.csv`.
4. **Candidatos v1**: exportar `references.bib` del v1 → `corpus/seeds/v1-candidates.csv`; los 27 pasan CI/CE como cualquier registro (los 6 no-indexados solo pueden entrar por aquí).
5. **Snowballing (1 ronda)**: backward = `referenced_works` (ya en el jsonl) de los INCLUIDOS + gold set; forward = `api.openalex.org/works?filter=cites:W<id>`. Cribar lo nuevo con la misma rúbrica; documentar cuántos entran por esta vía.
6. **PDFs de incluidos**: recuperar a mano los que falten (271 landings + 98 bloqueados, solo los incluidos).
7. **Extracción** con §7.6 (congelar el formulario tras la calibración): una fila por incluido → tablas del paper (RQ1-7) salen de ahí.
8. **Digestión al prototipo** (§7.4): digest tipado por paper (problema·mecanismo·operaciones·representación·evidencia·números·aplicabilidad-MF·cita), **prioridad = facetas escasas (WRITE, NEGATIVO, FIDELIDAD) y luego |F|**; lectura masiva delegable a verifier/Haiku (ADR-017), el juicio caro solo revisa el residuo.
9. **Literatura gris** (§6): snapshots fechados (PDF + manifest con sha256) de las 11 semillas + barrido mensual `site:`. Si la extensión Chrome conecta, lo hace el agente.
10. **Escritura del SMS v2**: estructura heredable del v1 (IEEEtran) pero con: delta metodológico v1→v2 (§1), auditoría de cadena como fortaleza metodológica, el mapa de vacíos por facetas (WRITE/NEGATIVO) como hallazgo, y la sección de práctica industrial (RQ7) desde la gris.
11. **Decisiones abiertas que solo Catalina puede tomar**: fecha de corte formal de la búsqueda · umbral definitivo de rúbrica (post-calibración) · si la pasada completa se delega o va a mano · destino de los huérfanos en `pdf/` · si el SMS v2 se escribe en `research/` o fuera del repo.

## 10. Commits de la sesión (research/)

`436b730` protocolo+tubería inicial · `4d8982e` conteos OpenAlex 143/429 · `06ae700` descarga local en un comando · `5cc380a`/`8e9f496`/`a93076b` fixes (atómico, arXiv 500, 429+SKIP_HARVEST) · `30da21f` v2.1 (Q2 + términos con evidencia + corpus run-1) · `550ea14` run 2 · `d817842` run 3 corpus cerrado · `3e223d0` v2.2 auditoría anti-v1 + gold set · `e603fe2` cribado diseñado · `937a5d8` facetas F · `3b56a77` conteos de facetas medidos.
