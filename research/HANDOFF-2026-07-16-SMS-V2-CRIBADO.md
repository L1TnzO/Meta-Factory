# HANDOFF — Pasada completa de cribado SMS v2 (2026-07-16)

> Para retomar con amnesia total: este doc + `SMS-V2-PROTOCOL.md` **§7.5 solamente** (la rúbrica
> CONGELADA — tu única autoridad de criterio) bastan. Todo lo afirmado aquí tiene commit; ante duda,
> `git log --oneline -- research/` es la verdad. NO re-derives anclas ni umbral: están congelados.

## 0. Qué es esto y estado en una línea

Tercera sesión SMS v2. Corpus CERRADO (1.069 únicos) · calibración EJECUTADA (50/50) · rúbrica y
formulario CONGELADOS (P1–P13 aceptadas por la ingeniera, protocolo v2.3) · **las 50 decisiones ya
están transferidas a `corpus/screening/screening_full.csv` → LA TAREA DE ESTA SESIÓN: decidir los
1.019 restantes.**

## 1. Contrato de cierre (qué debe ser verdad al terminar — hojas, no narrativa)

1. `screening_full.csv` con `decision` en 1.069/1.069 filas (el commit de la hoja = procedencia de
   cada exclusión; ADR-010).
2. TODA la zona GRIS + todo PRE-OUT-que-el-modelo-quiera-incluir verificados por la ingeniera
   (la decisión de borde es SIEMPRE humana — §7.5 congelado).
3. `corpus/artifacts.csv` poblado con los CE-5 subtipo herramienta que aparezcan (4 ya catalogados).
4. Bitácora §8 del protocolo actualizada con los números de la pasada + handoff para la fase
   siguiente (snowballing/extracción). Ningún nodo de §3 se avanza con hijos abiertos.

## 2. Cómo (vinculante — decisiones ya tomadas, no re-discutir)

- **Rúbrica**: protocolo §7.5 tal cual (CONGELADA 2026-07-16). Slice rule: NO leer el protocolo
  entero; §7.5 + este doc bastan para cribar.
- **Modo recomendado** (ADR-017/027, aceptado por la ingeniera en §7.5.3): delegar por LOTES a
  modelo barato con rúbrica-como-DATA. El evaluator recibe: anclas M/T/E/F + tabla CI/CE + 5
  ejemplos resueltos de la calibración como few-shot — sugeridos: W4416611586 (IN 3/2/1, evidencia
  negativa), W7129523991 (OUT-CE1: scratchpad intra-tarea, P1), W7156942111 (OUT-CE5: manifiesto
  no-estudio), W7117411283 (GRIS: E=0 solo-Zenodo, P3), W4415524435 (OUT-CE2: T=0 pese a M=3).
  Devuelve M/T/E/F/decision/nota-de-1-línea por registro. Verificación humana OBLIGATORIA: 10%
  aleatorio + toda su GRIS + todo PRE-OUT rescatado.
- **Abstract COMPLETO siempre** desde `corpus/merged/corpus.jsonl` (la hoja trae solo 400 chars);
  unir por `key` (= `record_key()` de `harvest/download_pdfs.py`). La calibración encontró 2
  veredictos que CAMBIAN con el abstract completo.
- **PDF solo para dudas puntuales** (598 en `corpus/pdf/<key>.pdf`, `pdftotext` disponible); jamás
  cargar PDFs al hilo principal (ADR-017) — la calibración resolvió 4 dudas con 3 páginas c/u.
- **Los hints (`sig_*`, `triage`) ordenan, NO deciden**: `sig_se` trae ~1/3 de espurios; los hints
  de facetas escasas tienen recall 0 (calibración §4–§5). Denominadores triage sobre los 1.069:
  PRE-IN 468 · GRIS 524 · PRE-OUT 77.
- **P12 activo**: papers que toquen estado-de-plan/progreso o traspaso entre sesiones/agentes →
  anotar en `notes` (con ~≥5 se promueve faceta `PLAN-ESTADO`).
- Registrar por lote en la bitácora: nº decididos, distribución, GRIS acumulados (da denominadores
  y hace auditable la delegación).

## 3. El árbol de trabajo (columna vertebral — estado de TODOS los nodos)

- [CERRADO] Búsqueda: cadena v2.1 congelada · corpus 1.069 · sanidad gold-set (runs 1–3).
- [CERRADO] v2.2 auditoría anti-v1 · diseño de cribado · facetas F.
- [CERRADO] Calibración 50/50 · P1–P13 · rúbrica+formulario congelados (v2.3) · transfer 50→full.
- [ABIERTO · ESTA SESIÓN] **Pasada completa: 1.019 pendientes en `screening_full.csv`.**
- [ABIERTO · Catalina, paralelo] Rescates CE-4p: AESP (ssrn id 6478861, bot-wall) · PDF de
  W7167425781 (Zenodo, INCLUIR ya decidido — es para digestión) · paper de ContextForge (dentro del
  zip del record W7155711670) · segunda opinión del único GRIS vivo: W7117411283 (SimpleMem).
- [ABIERTO · después, en orden] candidatos v1 (`references.bib` → `corpus/seeds/v1-candidates.csv`)
  → snowballing 1 ronda (backward `referenced_works` ya en el jsonl; forward `cites:W<id>`) → PDFs
  de incluidos (recuperación manual solo incluidos) → extracción §7.6 (CONGELADO) → digestión §7.4
  (prioridad: facetas escasas WRITE/NEGATIVO/FIDELIDAD + |F|; arrancar por los ★ de la calibración:
  W7167425781, W7160968832, W7162218979, W7148175972, W7140953560, 2510.23730v2, y W4416611586 como
  advertencia) → cosecha gris §6 → escritura SMS v2.
- [DECISIONES ABIERTAS · solo Catalina] fecha de corte formal de la búsqueda · destino de huérfanos
  en `pdf/` · dónde se escribe el SMS (¿`research/`?).

## 4. Decisiones de la ingeniera en esta sesión (vinculantes)

1. Calibración delegada al agente y ACEPTADA tras revisión («Sí, está ok») — con pasada final
   adversarial que corrigió DOIs de `artifacts.csv`.
2. **P1–P13 aceptadas** → rúbrica congelada (el detalle de cada propuesta y su porqué:
   `SMS-V2-CALIBRATION-2026-07-16.md` §6 y §9).
3. El SMS se orienta a sus 4 preguntas núcleo (trazabilidad en calibración §9): organización +
   retrieval de memoria masiva en repos de larga vida (Q1) · medición de retrieval en el harness
   (Q2) · handoff punteros-vs-contenido (Q3) · estado-de-plan con cierre verificable (Q4, necesidad
   nueva §2). La literatura manda; lo implementado en MF son hipótesis a confirmar/falsear.
4. Umbral ≥4 con M≥1 se MANTIENE (P10); handoffs con punteros+razones, no listas prescriptivas.

## 5. Quirks de entorno (heredados 2026-07-15 + nuevos de hoy)

- Sandbox de Cowork NO alcanza api.openalex.org/arxiv.org (proxy 403 allowlist) — irrelevante para
  la pasada (todo es local); vuelve a importar en snowballing forward (máquina de la ingeniera o
  extensión Chrome si conecta).
- SSRN tras bot-wall (probado con id correcto 6478861); `web_fetch` no renderiza JS ni URLs largas.
- **Git locks tras CADA commit desde el sandbox**: pedir permiso de borrado UNA vez
  (`allow_cowork_file_delete`) y luego `rm -f .git/*.lock .git/objects/maintenance.lock` antes y
  después de commitear. Commits estilo `tipo(SMS-V2): ...` + trailer
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- **NO re-ejecutar `make_screening_sheet.py`** sobre las hojas: regeneraría con decisiones VACÍAS
  (warning en el propio script). El cambio P7 de `DIVERGENT_TERMS` es solo para reproducibilidad.
- Hay cambios ajenos sin commitear en el repo (helpdesk frontend, `presentation/`, zip de snipeit):
  NO tocarlos ni incluirlos en commits de research/.

## 6. Punteros con razón (no prescriptivos — re-deriva tu plan si las razones no aplican)

- `SMS-V2-PROTOCOL.md` **§7.5** — LA rúbrica congelada; léela entera antes del primer lote.
- `SMS-V2-CALIBRATION-2026-07-16.md` **§8** — los 50 resueltos en una tabla (cantera de few-shot);
  **§3–§5** — el porqué de cada ancla (leer SOLO si un borde confunde).
- `corpus/screening/screening_full.csv` — tu hoja de trabajo (1.019 filas con `decision` vacía).
- `HANDOFF-2026-07-15-SMS-V2.md` — historia de la fase de búsqueda (solo si necesitas contexto).

## 7. Commits de esta sesión (research/)

`e171707` calibración 50/50 + informe P1–P10 · `9533d36` §9 trazabilidad Q1–Q4 + P11–P13 ·
`ddb058f` fix DOIs artifacts.csv (pasada adversarial) · `4618c1c` rúbrica CONGELADA v2.3 + GRIS
resueltos + transfer 50→full · (este doc) handoff.
