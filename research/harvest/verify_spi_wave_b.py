#!/usr/bin/env python3
"""Diente de la fase B — el corpus se EXTIENDE con los 13 elegibles de la SPI, nada más se mueve.

Escrito ANTES que la derivación (mismo patrón que `verify_spi_apply.py` / `verify_claims_spi.py`) y
FUERA del radio del slot que hará el trabajo: el slot puede escribir extraction.csv, digest.jsonl y
los chunks e72+/d72+, pero no este archivo. El objetivo del universo (qué claves deben aparecer) se
lee de `corpus/spi/APPLIED.json::digest_eligible` — no se hardcodea una lista que pueda desincronizarse.

Invariantes (cada uno falsable, probado de los dos lados antes de commitear):
  W-1  las 13 (o las que APPLIED.json declare) claves elegibles están en extraction.csv, pdf_status=ok,
       y su fila pasa `extraction_law.validate_row` sin errores (cumplimiento §7.6 real, no sólo "no vacío").
  W-2  esas mismas claves tienen un registro en digest.jsonl que pasa `digestion_law.validate_digest`
       contra su propia fila de extracción (facetas ligadas, §7.4).
  W-3  ninguna fila de extraction.csv AJENA a las elegibles cambió una sola celda respecto al HEAD de git
       (el ensanche del corpus no reescribe lo ya congelado).
  W-4  ningún registro de digest.jsonl ajeno cambió respecto al HEAD de git (misma garantía en digestión).
  W-5  los chunks e01..e71 y d01..d71 (los ya existentes antes de esta ola) son BYTE-IDÉNTICOS al HEAD.
  W-6  extraction.csv creció en EXACTAMENTE len(elegibles) filas (nunca se borra una fila existente) y
       lo mismo digest.jsonl.
  W-7  `corpus/spi/**` no cambió una sola línea (esta ola no re-deriva la SPI, sólo consume su veredicto).

Falla CERRADO: si falta un artefacto de entrada, es rojo, no "no aplica".

Nota sobre `--base-ref` (defecto ROJO ENCONTRADO 2026-07-27, corregido el mismo día): W-3..W-7
comparan contra un punto de referencia en git para detectar cambios AJENOS. La ola B es
MULTI-COMMIT por diseño (slot de extracción committeado antes de abrir el de digestión, §5 del
handoff: "commit → clear_slot" entre olas) — así que "HEAD" deja de significar "el estado antes
de esta ola" en cuanto el primer slot se commitea; el segundo slot mediría su propio trabajo
contra un HEAD que YA incluye el primero, y una comparación ajena-vs-HEAD que en realidad debía
ser ajena-vs-antes-de-la-ola queda ciega a los cambios legítimos del slot anterior (falso rojo:
"0 filas añadidas" cuando las 13 sí se añadieron, sólo que en un commit previo). Por eso
`--base-ref` es explícito y NO por defecto "HEAD": para esta ola concreta es el commit del propio
gate, `29104ec` (el estado justo antes de que arrancara el primer slot) — un valor FIJO a
propósito, porque este gate mide UNA transición histórica concreta (§9.3 fase B), no es una
herramienta genérica reusable entre olas futuras como sí lo son verify_spi_apply.py/
verify_claims_spi.py.

Uso:  python3 harvest/verify_spi_wave_b.py [--root DIR] [--base-ref REF] [-v]
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extraction_law  # noqa: E402
import digestion_law  # noqa: E402

# El estado justo ANTES de que arrancara el primer slot de la ola B (commit del propio gate).
# Fijo a propósito -- ver la nota de módulo sobre por qué "HEAD" es la referencia equivocada una
# vez que la ola cruza más de un commit.
DEFAULT_BASE_REF = "29104ec"


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _git_show(root: Path, rel: str, base_ref: str) -> str | None:
    """Contenido de `rel` en `base_ref`, o None si no existía ahí (recién creado por la ola)."""
    r = subprocess.run(["git", "show", f"{base_ref}:{rel}"], cwd=root, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def check(root: Path, verbose: bool = False, base_ref: str = DEFAULT_BASE_REF) -> list[str]:
    bad: list[str] = []

    applied_path = root / "corpus/spi/APPLIED.json"
    if not applied_path.exists():
        return ["W-1 falta corpus/spi/APPLIED.json — el gate falla CERRADO"]
    applied = json.loads(applied_path.read_text(encoding="utf-8"))
    elegibles = set(applied["digest_eligible"])
    if not elegibles:
        return ["W-1 APPLIED.json::digest_eligible está vacío — nada que verificar (¿universo equivocado?)"]

    ext_path = root / "corpus/extraction/extraction.csv"
    dig_path = root / "corpus/digestion/digest.jsonl"
    if not ext_path.exists() or not dig_path.exists():
        return ["W-1 falta extraction.csv o digest.jsonl — el gate falla CERRADO"]

    ext_rows = _read_csv(ext_path)
    ext_by_key = {r["key"]: r for r in ext_rows}
    dig_rows = _read_jsonl(dig_path)
    dig_by_key = {r["key"]: r for r in dig_rows}

    # --- W-1 / W-2: las elegibles están, y pasan la ley congelada -----------------------------------
    for key in sorted(elegibles):
        row = ext_by_key.get(key)
        if row is None:
            bad.append(f"W-1 clave elegible '{key}' no está en extraction.csv")
            continue
        if row.get("pdf_status") != "ok":
            bad.append(f"W-1 '{key}' está en extraction.csv pero pdf_status={row.get('pdf_status')!r} != 'ok'")
        # validate_row exige el field-set EXACTO de VERDICT_COLUMNS (sin las columnas de identidad
        # source/year/title/pdf_status/F_screening que sólo viven en extraction.csv) -- recortar antes.
        verdict_only = {c: row.get(c, "") for c in extraction_law.VERDICT_COLUMNS}
        errs = extraction_law.validate_row(verdict_only)
        if errs:
            bad.append(f"W-1 '{key}' viola extraction_law: {errs[0]}" +
                       (f" (+{len(errs)-1} más)" if len(errs) > 1 else ""))

        drec = dig_by_key.get(key)
        if drec is None:
            bad.append(f"W-2 clave elegible '{key}' no tiene registro en digest.jsonl")
            continue
        derrs = digestion_law.validate_digest(drec, row)
        if derrs:
            bad.append(f"W-2 '{key}' viola digestion_law: {derrs[0]}" +
                       (f" (+{len(derrs)-1} más)" if len(derrs) > 1 else ""))

    # --- W-3 / W-6: extraction.csv — ninguna fila AJENA cambió, sólo se AÑADE ------------------------
    head_ext_text = _git_show(root, "research/corpus/extraction/extraction.csv", base_ref)
    if head_ext_text is None:
        bad.append(f"W-3 no se pudo leer extraction.csv en {base_ref} (git show falló) — gate falla CERRADO")
    else:
        head_rows = {r["key"]: r for r in csv.DictReader(head_ext_text.splitlines())}
        changed_foreign = [k for k, r in ext_by_key.items()
                           if k not in elegibles and k in head_rows and r != head_rows[k]]
        if changed_foreign:
            bad.append(f"W-3 {len(changed_foreign)} fila(s) AJENA(S) a las elegibles cambiaron en "
                       f"extraction.csv: {changed_foreign[:3]}")
        missing = [k for k in head_rows if k not in ext_by_key]
        if missing:
            bad.append(f"W-3 {len(missing)} fila(s) que existían en {base_ref} desaparecieron de "
                       f"extraction.csv: {missing[:3]}")
        added = set(ext_by_key) - set(head_rows)
        if added != elegibles:
            bad.append(f"W-6 filas añadidas a extraction.csv ({len(added)}) != elegibles declaradas "
                       f"({len(elegibles)}): sobran {sorted(added - elegibles)[:3]} · "
                       f"faltan {sorted(elegibles - added)[:3]}")

    # --- W-4 / W-6: digest.jsonl — misma garantía --------------------------------------------------
    head_dig_text = _git_show(root, "research/corpus/digestion/digest.jsonl", base_ref)
    if head_dig_text is None:
        bad.append(f"W-4 no se pudo leer digest.jsonl en {base_ref} (git show falló) — gate falla CERRADO")
    else:
        head_dig = {json.loads(l)["key"]: json.loads(l)
                    for l in head_dig_text.splitlines() if l.strip()}
        changed_foreign = [k for k, r in dig_by_key.items()
                           if k not in elegibles and k in head_dig and r != head_dig[k]]
        if changed_foreign:
            bad.append(f"W-4 {len(changed_foreign)} registro(s) AJENO(S) cambiaron en digest.jsonl: "
                       f"{changed_foreign[:3]}")
        missing = [k for k in head_dig if k not in dig_by_key]
        if missing:
            bad.append(f"W-4 {len(missing)} registro(s) que existían en {base_ref} desaparecieron de "
                       f"digest.jsonl: {missing[:3]}")
        added = set(dig_by_key) - set(head_dig)
        if added != elegibles:
            bad.append(f"W-6 registros añadidos a digest.jsonl ({len(added)}) != elegibles declaradas "
                       f"({len(elegibles)}): sobran {sorted(added - elegibles)[:3]} · "
                       f"faltan {sorted(elegibles - added)[:3]}")

    # --- W-5: los chunks previos a esta ola son byte-idénticos a base_ref ----------------------------
    for sub, prefix in (("extraction", "e"), ("digestion", "d")):
        bdir = root / f"corpus/{sub}/batches"
        for path in sorted(bdir.glob(f"{prefix}[0-9][0-9].*")):
            rel = f"research/corpus/{sub}/batches/{path.name}"
            head_txt = _git_show(root, rel, base_ref)
            if head_txt is None:
                continue  # chunk nuevo de esta ola (e72+/d72+), no existía en base_ref -- no aplica W-5
            if path.read_text(encoding="utf-8") != head_txt:
                bad.append(f"W-5 el chunk pre-existente '{path.name}' cambió respecto a {base_ref} "
                           f"(los chunks ya cerrados no se tocan)")

    # --- W-7: la SPI no se re-derivó --------------------------------------------------------------
    # `git diff -- <path>` es relativo al CWD (a diferencia de `git show REF:<path>`, root-relative);
    # se resuelve el toplevel real del repo para no depender de cómo se pasó --root.
    toplevel = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root,
                              capture_output=True, text=True).stdout.strip()
    if toplevel:
        r = subprocess.run(["git", "diff", "--quiet", base_ref, "--", "research/corpus/spi/"], cwd=toplevel)
        if r.returncode != 0:
            bad.append(f"W-7 corpus/spi/ cambió respecto a {base_ref} — esta ola consume la SPI, "
                       f"no la re-deriva")

    if verbose:
        print(f"[wave-b] elegibles={len(elegibles)} extraction_rows={len(ext_rows)} "
              f"digest_rows={len(dig_rows)}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]),
                    help="raíz de research/ (por defecto, la del propio archivo)")
    ap.add_argument("--base-ref", default=DEFAULT_BASE_REF,
                    help=f"commit/ref anterior a la ola completa (defecto: {DEFAULT_BASE_REF}, "
                         f"el commit del propio gate — ver nota de módulo)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    bad = check(Path(args.root), verbose=args.verbose, base_ref=args.base_ref)
    if bad:
        print(f"RED: {len(bad)} invariante(s) rotos — la ola B no respeta el contrato de ensanche")
        for b in bad:
            print(f"  - {b}")
        return 1
    print("GREEN: los elegibles entraron a extraction.csv+digest.jsonl; nada ajeno se movió")
    return 0


if __name__ == "__main__":
    sys.exit(main())
