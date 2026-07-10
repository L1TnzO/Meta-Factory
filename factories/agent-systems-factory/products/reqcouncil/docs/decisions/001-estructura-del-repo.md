# 001 — Estructura del repositorio (2026-07-05)

**Estado:** aceptada · **Inmutable** (correcciones → nueva decisión que la supersede).

## Contexto
Tras la sesión fundacional el top-level mezclaba: diseño v2, diseño v1 (`Idea/`), informe,
datasets curados, 4 paquetes crudos descargados (787 MB en uno), un survey suelto y un `.env`
sin ignorar. No existía hogar para código ni docs de trabajo por hito.

## Decisión
```
reqcouncil/   código (multi-archivo por responsabilidad; sin monolitos)
tests/        gates deterministas por hito (H1: paridad byte-exacta)
config/       umbrales · modelo · chunking = DATA versionada
datasets/     corpora golden curados (read-only) · _originals/ = crudos, UNTRACKED
docs/         STATE (overwrite) · LOG (append) · work/ (por hito) · decisions/ (inmutable)
              design/ (v2 canónico) · informe/ (UFRO) · reference/ (survey) · history/ (v1)
runs/         salidas (gitignorado)
```
- `.env` ignorado; `.env.example` documenta las claves (DEEPSEEK_API_KEY, se usa desde H2).
- Los crudos quedan localmente como provenance pero fuera de git (los curados en
  `datasets/<corpus>/` conservan READMEs/licencias originales).
- Espejo deliberado del esquema Meta-Factory (STATE/LOG/work/decisions) porque este producto se
  gobierna igual: cierre por gate + memoria por tipo de mutación.

## Consecuencias
- Referencias `../datasets/` desde design → `../../datasets/`; informe→design queda como hermano
  bajo `docs/` (sin cambio). Historia git preservada vía `git mv`.
- El paquete original de Inter2US dentro de `datasets/inter2us/` sigue siendo la fuente de verdad
  del golden; el arnés no lo muta jamás.
