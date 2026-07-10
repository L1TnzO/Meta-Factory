# ReqCouncil — elicitación de requisitos desde transcripciones (proyecto de titulación)

Sistema multi-agente (LLM: **DeepSeek-V4-Flash @ SiliconFlow**, decisión 004) que recibe la **transcripción** de una reunión de
elicitación y produce un borrador **calibrado y trazable** de requisitos de software mediante un
**council de personas que delibera en loops** hasta consenso — evaluado contra golden sets públicos
(eval-driven, con gates bloqueantes). El audio (Whisper/ASR) está fuera de alcance: la
transcripción llega hecha.

**Punto de entrada único: [`docs/STATE.md`](docs/STATE.md)** (estado de hoy + próximo paso).

## Estructura
| Ruta | Qué es |
|---|---|
| `reqcouncil/` | Código (Python 3.12, multi-archivo). Hoy: `ingest/` (H1 ✅) + `store/schema.sql`; el resto llega por hitos H2–H6 |
| `tests/` | Gates deterministas por hito — H1: `test_chunk_parity.py` (paridad **byte-exacta** con el CSV golden de Inter2US) |
| `config/` | Umbrales de gates, modelo y chunking como **DATA versionada** (cambiarlos exige motivo escrito) |
| `datasets/` | Corpora golden curados, **read-only** (Inter2US · ReqElicitBench · WEPGCOMP/+Lugar · RECOVER) — ver su README; `_originals/` = paquetes crudos descargados (fuera de git) |
| `docs/STATE.md` · `docs/LOG.md` | Verdad de hoy (overwrite) · historia cerrada (append) |
| `docs/work/` | Un doc por hito con contrato + evidencia del gate (H1 cerrado) |
| `docs/decisions/` | Decisiones inmutables (001 = esta estructura) |
| `docs/design/` | **Diseño unificado v2 (vigente)** — overview, protocolo del council, grounding, arnés de evaluación, plan por hitos |
| `docs/informe/` | **Informe Final UFRO** — redactado como sistema desarrollado; pendientes marcados `[FALTA DATO]` (ver su README) |
| `docs/reference/` | Survey propio de datasets y estado del arte (insumo del Cap. 2) |
| `docs/history/Idea/` | Diseño v1 histórico (superado por v2; registro inmutable) |
| `runs/` | Salidas de corridas (gitignorado) |

## Uso (H1)
```bash
python3 -m pytest                      # gates (H1: 6 tests, paridad byte-exacta)
python3 -m reqcouncil ingest datasets/inter2us/data/public_interview/int1.txt   # transcript → chunks CSV
```
Sin dependencias de terceros hasta H2 (`pip install -e .[council,dev]` cuando llegue el runtime).
Secretos: copiar `.env.example` → `.env` (gitignorado); `DEEPSEEK_API_KEY` se usa desde H2.

## Estado (2026-07-05)
- ✅ Diseño v2 · datasets curados · informe avanzado al máximo sin ejecución.
- ✅ **H1 Ingesta** cerrado por gate verde (`docs/work/H1-INGEST-INCREMENT.md`).
- ⏳ H2 Juez (E0): calibración contra los 760 pares humanos (`docs/design/04 §3`).

## Relación con ASF (Meta-Factory)
El diseño cumple deliberadamente el blueprint de producto de la **Agent Systems Factory**
(topología LangGraph tipada y compilable, HITL no-salteable por alcanzabilidad, estado durable,
provenance, gates que bloquean). ASF está hoy REGRESSION-FROZEN, por eso este repo es el hogar
standalone; al descongelarse, ReqCouncil es generable como producto ASF (`docs/design/00 §4`).
