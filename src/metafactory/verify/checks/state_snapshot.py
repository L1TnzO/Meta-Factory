"""state_snapshot (ADR-019 §3, M1) — la sección «## Ahora» de STATE es un SNAPSHOT (verdad-de-hoy
acotada), no un log. El único artefacto OVERWRITE del esquema (ADR-007) es también la única superficie
de drift: si se la deja crecer, «leé STATE» cuesta ~20k tokens y acumula afirmaciones rancias.

Diente dos-lados, hermano de `column_parity` en estilo. Falla si «Ahora»:
  (a) EXCEDE el presupuesto de líneas (`NOW_BUDGET_LINES`) — la historia cerrada va a LOG, no acá; o
  (b) contiene una MARCA DE CIERRE (✅/CERRADO/COMPLETE/DONE) cuya fecha más reciente en la línea es más
      vieja que `STALE_CLOSURE_DAYS` — un cierre fechado y viejo ya debería haber DESCENDIDO a LOG.

NO auto-reescribe (auto-reescribir es lo que causa la deriva; ADR-019 §Rechazado): FALLA y SEÑALA. La
proyección de hechos (bloque `meta:projection`, generado) NO es «Ahora» y queda fuera — se mide sólo la
PROSA editable bajo el encabezado `## Ahora`.

Argv: <meta_root> [--now YYYY-MM-DD]. Exit 0 = PASS (snapshot acotado y fresco + diente vivo),
1 = FAIL (presupuesto excedido / cierre rancio / diente decorativo)."""
from __future__ import annotations

import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

# ── presupuesto (ADR-019 §3: «Ahora» ≤ ~40 líneas de verdad-de-hoy; headroom mínimo para el snapshot) ──
NOW_BUDGET_LINES = 45
STALE_CLOSURE_DAYS = 14

# Marcas de cierre: el emoji ✅ o las palabras en MAYÚSCULA tal como el proyecto las escribe (evita
# falsos positivos de prosa minúscula como "complete" o "done" dentro de otra palabra). `CLOSED` cubre
# el header English-forward `Status: **CLOSED**` (ADR-026, dual-accept con el legacy `CERRADO`).
_CLOSURE_RE = re.compile(r"✅|\b(?:CERRAD[OA]|CLOSED|COMPLET[OAE]|DONE)\b")
_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_NOW_HEADING_RE = re.compile(r"^##\s+Ahora\b")


def extract_now_lines(text: str) -> list[str] | None:
    """Las líneas de contenido bajo `## Ahora …` (sin el encabezado), hasta el próximo `## ` o EOF,
    recortando blancos al inicio/fin. None si no hay sección «Ahora». Robusto a que sea la última."""
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if _NOW_HEADING_RE.match(ln)), None)
    if start is None:
        return None
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    body = lines[start + 1:end]
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    return body


def _stale_closures(body: list[str], today: date) -> list[str]:
    """Líneas con marca de cierre cuya fecha más RECIENTE es más vieja que el umbral. Una marca sin
    fecha no se flaggea (no se puede medir staleness; el presupuesto la gobierna)."""
    problems: list[str] = []
    for ln in body:
        if not _CLOSURE_RE.search(ln):
            continue
        dates = []
        for y, m, d in _DATE_RE.findall(ln):
            try:
                dates.append(date(int(y), int(m), int(d)))
            except ValueError:
                pass
        if not dates:
            continue
        newest = max(dates)
        age = (today - newest).days
        if age > STALE_CLOSURE_DAYS:
            snippet = ln.strip()[:80]
            problems.append(f"cierre rancio ({age}d > {STALE_CLOSURE_DAYS}d, {newest.isoformat()}): {snippet}")
    return problems


def snapshot_problems(state_path: Path, today: date) -> list[str]:
    """[] si «Ahora» es un snapshot acotado y fresco. Lista de problemas si no."""
    try:
        text = state_path.read_text(encoding="utf-8")
    except OSError as e:  # noqa: BLE001 — un STATE ilegible es reportable, no un crash
        return [f"no pude leer {state_path}: {e}"]
    body = extract_now_lines(text)
    if body is None:
        return ["no encontré la sección `## Ahora` en STATE.md (¿se renombró el encabezado?)"]
    problems: list[str] = []
    n = len(body)
    if n > NOW_BUDGET_LINES:
        problems.append(f"«Ahora» = {n} líneas > presupuesto {NOW_BUDGET_LINES} "
                        f"(bajá lo cerrado/histórico a LOG; el snapshot es verdad-de-HOY + punteros)")
    problems.extend(_stale_closures(body, today))
    return problems


def _tooth_bites(today: date) -> bool:
    """Diente RED dos-lados: cada modo de falla DEBE morder sobre un testigo sintético. Si alguno no
    muerde, el check es decorativo → FAIL."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        sp = Path(td) / "STATE.md"
        # (a) sobre-presupuesto: «Ahora» con muchas más líneas que el budget, sin cierres.
        over = "\n".join(f"- bullet {i}" for i in range(NOW_BUDGET_LINES + 10))
        sp.write_text(f"# S\n## Ahora\n{over}\n## Siguiente\n- x\n", encoding="utf-8")
        bites_budget = any("presupuesto" in p for p in snapshot_problems(sp, today))
        # (b) cierre rancio: bajo presupuesto, pero un ✅ fechado más viejo que el umbral.
        old = (today.toordinal() - (STALE_CLOSURE_DAYS + 30))
        old_iso = date.fromordinal(old).isoformat()
        sp.write_text(f"# S\n## Ahora\n- algo viejo ✅ ({old_iso})\n## Siguiente\n- x\n", encoding="utf-8")
        bites_stale = any("rancio" in p for p in snapshot_problems(sp, today))
    return bites_budget and bites_stale


def _parse_now(argv: list[str]) -> date:
    if "--now" in argv:
        i = argv.index("--now")
        if i + 1 < len(argv):
            return datetime.strptime(argv[i + 1], "%Y-%m-%d").date()
    return datetime.now(timezone.utc).date()


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    meta_root = Path(args[0]).resolve() if args else Path.cwd()
    today = _parse_now(argv)
    state_path = meta_root / "docs" / "STATE.md"

    problems = snapshot_problems(state_path, today)
    if problems:
        print("STATE_SNAPSHOT ROJO — «Ahora» dejó de ser un snapshot (ADR-019 §3):")
        for p in problems:
            print(f"  ✗ {p}")
        print("  -> podá «Ahora» a verdad-de-HOY + punteros; bajá lo cerrado/histórico a `docs/LOG.md` (append).")
        return 1

    if not _tooth_bites(today):
        print("STATE_SNAPSHOT DECORATIVO — el analizador no marcó un «Ahora» inflado/rancio sintético → sin dientes")
        return 1

    body = extract_now_lines(state_path.read_text(encoding="utf-8")) or []
    print(f"OK state_snapshot: «Ahora» = {len(body)} líneas ≤ {NOW_BUDGET_LINES}; "
          f"sin cierres rancios (>{STALE_CLOSURE_DAYS}d); diente RED vivo (presupuesto + rancio)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
