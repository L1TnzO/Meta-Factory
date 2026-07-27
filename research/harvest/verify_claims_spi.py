#!/usr/bin/env python3
"""Diente: el ledger de claims deriva de la SPI APLICADA, no de la pasada 1.

Se escribe ANTES que la derivación y vive FUERA de su radio (mismo patrón que `verify_spi_apply.py`).
No lee el código del derivador: **recomputa por su cuenta** las poblaciones post-SPI desde
`corpus/spi/APPLIED.json` + el corpus crudo, y las compara contra los valores EMITIDOS en
`sms-v2/claims.tex`. Dos implementaciones independientes que coinciden es lo que hace que un verde
signifique algo; un verde de una sola implementación sólo dice que el código corre.

Contrato normativo: `SMS-V2-CLAIMS-CONTRACT.md`. Invariantes I-1..I-8 (ver §6 del contrato).

Falla CERRADO: si falta un artefacto de entrada, es rojo, no «no aplica».

Uso:  python3 harvest/verify_claims_spi.py [--root DIR] [-v]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

# ------------------------------------------------------------------ vocabulario cerrado (contrato §3)
PASADAS = {"flujo1", "spi", "post"}
RAW_NAMES = {"digest", "extraction", "sheet_full", "sheet_snowball"}
V2_NAMES = {"digest_v2", "corpus_v2", "extraction_v2"}
SPI_NAMES = {"spi", "conflicts", "applied"}

# Amenazas que el paper DEBE citar (contrato §5.4). El residuo que no se imprime está escondido.
THREAT_MACROS = ("clPostExclusionesSoloTitulo", "clPostBloqueadosSinTexto", "clPostDegradados")

MACRO_RE = re.compile(r"^\\newcommand\{\\(cl[A-Za-z]+)\}\{(.*)\}\s*$", re.M)
KAPPA_RE = re.compile(r"Cohen\s+κ\s*=\s*\*{0,2}([0-9]+[.,][0-9]+)")
NUMLIT_RE = re.compile(r"(?<![A-Za-z_])\d")


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _num(text: str) -> float:
    """Deshace el formato tipográfico español: '1.069' -> 1069 · '0,895' -> 0.895."""
    return float(text.strip().replace(".", "").replace(",", ".")) if "," in text else float(
        text.strip().replace(".", ""))


def _uses(expr: str, name: str) -> bool:
    """Frontera de palabra: `digest` NO hace match dentro de `digest_v2` ('_' es carácter de palabra)."""
    return re.search(rf"\b{re.escape(name)}\b", expr) is not None


# ------------------------------------------------------------------ recomputación independiente (§2)
class Universe:
    """Las poblaciones post-SPI, recomputadas desde APPLIED.json + corpus crudo."""

    def __init__(self, root: Path) -> None:
        applied = json.loads((root / "corpus/spi/APPLIED.json").read_text(encoding="utf-8"))
        delta = applied["membership_delta"]
        keys_of = lambda eff: {r["key"] for r in delta if r["effect"] == eff}  # noqa: E731

        self.applied = applied
        self.degradadas = keys_of("DEGRADED")
        self.admitidas = keys_of("ADD_INCLUIR")
        self.excluidas = keys_of("ADD_EXCLUIR")
        self.fusion = {p["from"]: p["into"] for p in applied["merged_into"]}
        self.human_rows = sum(1 for r in delta if r["effect"] == "HUMAN_QUEUE")
        self.human_keys = keys_of("HUMAN_QUEUE")
        self.elegibles = set(applied["digest_eligible"])
        self.bloqueados = set(applied["digest_blocked_no_fulltext"])
        self.solo_titulo = int(applied["counts"]["title_only_exclusions"])

        self.digest_raw = {r["key"] for r in _read_jsonl(root / "corpus/digestion/digest.jsonl")}
        self.extraction_raw = {r["key"] for r in _read_csv(root / "corpus/extraction/extraction.csv")}
        self.conflict_rows = len(_read_csv(root / "corpus/spi/CONFLICTOS.csv"))

        # Fusionar colapsa IDENTIDAD, no evidencia (contrato §2): la fila digerida de un `from`
        # sobrevive bajo la identidad de su `into`, aunque el `into` no tenga digest propio.
        self.digest_v2 = {self.ident(k) for k in self.digest_raw
                          if k not in self.degradadas and self.ident(k) not in self.degradadas}
        self.corpus_v2 = {self.ident(k) for k in (self.extraction_raw | self.admitidas)
                          if k not in self.degradadas and self.ident(k) not in self.degradadas}
        self.pendientes = {k for k in self.elegibles if self.ident(k) not in self.digest_v2}

        kappa = self._kappa(root / "corpus/spi/AGREEMENT.md")
        self.kappa_colapsado, self.kappa_exacto = kappa

    def ident(self, key: str) -> str:
        return self.fusion.get(key, key)

    @staticmethod
    def _kappa(path: Path) -> tuple[float | None, float | None]:
        """κ reportado por la VISTA `AGREEMENT.md` — sólo para cruzar contra el κ derivado (I-8)."""
        col = exa = None
        for line in path.read_text(encoding="utf-8").splitlines():
            m = KAPPA_RE.search(line)
            if not m:
                continue
            # OJO: AGREEMENT.md escribe κ con punto decimal ('0.895'); claims.tex con coma ('0,895').
            # Aquí NO se usa _num (que trata el punto como separador de miles).
            valor = float(m.group(1).replace(",", "."))
            if "COLAPSADO" in line.upper() and col is None:
                col = valor
            elif "EXACTO" in line.upper() and exa is None:
                exa = valor
        return col, exa

    def expected(self) -> dict[str, tuple[str, float | None]]:
        """Ids de carga (contrato §4) -> (pasada exigida, valor recomputado; None = sólo cruzado)."""
        return {
            "clPostDigest": ("post", len(self.digest_v2)),
            "clPostCorpus": ("post", len(self.corpus_v2)),
            "clPostDegradados": ("post", len(self.degradadas)),
            "clPostFusiones": ("post", len(self.fusion)),
            "clPostAdmitidosSpi": ("post", len(self.admitidas)),
            "clPostExcluidosSpi": ("post", len(self.excluidas)),
            "clPostBloqueadosSinTexto": ("post", len(self.bloqueados)),
            "clPostPendientesDigest": ("post", len(self.pendientes)),
            "clPostExclusionesSoloTitulo": ("post", self.solo_titulo),
            "clFiaKappaColapsado": ("spi", self.kappa_colapsado),
            "clFiaKappaExacto": ("spi", self.kappa_exacto),
            "clFiaColaHumanaFilas": ("spi", self.human_rows),
            "clFiaColaHumana": ("spi", len(self.human_keys)),
            "clFiaConflictosFilas": ("spi", self.conflict_rows),
        }


# ------------------------------------------------------------------ invariantes
def check(root: Path, verbose: bool = False) -> list[str]:
    bad: list[str] = []

    def need(rel: str) -> Path | None:
        p = root / rel
        if not p.exists():
            bad.append(f"I-3 falta el artefacto '{rel}' — el gate falla CERRADO, no 'no aplica'")
            return None
        return p

    for rel in ("corpus/spi/APPLIED.json", "corpus/digestion/digest.jsonl",
                "corpus/extraction/extraction.csv", "corpus/spi/CONFLICTOS.csv",
                "corpus/spi/AGREEMENT.md", "sms-v2/claims.yml"):
        need(rel)
    if bad:
        return bad

    import yaml  # dependencia ya usada por verify_sms_claims.py

    u = Universe(root)
    claims = yaml.safe_load((root / "sms-v2/claims.yml").read_text(encoding="utf-8")) or []
    by_id = {str(c.get("id", "")).strip(): c for c in claims}

    # --- I-1 esquema: `pasada` obligatorio, vocabulario cerrado -----------------------------------
    sin_pasada = [c.get("id", "?") for c in claims if str(c.get("pasada", "")).strip() not in PASADAS]
    if sin_pasada:
        bad.append(f"I-1 {len(sin_pasada)}/{len(claims)} claims sin 'pasada' válida "
                   f"{{{'|'.join(sorted(PASADAS))}}} — p.ej. {', '.join(map(str, sin_pasada[:4]))}")

    # --- I-2 aislamiento por pasada (estático, decidible) -----------------------------------------
    for c in claims:
        cid, pas, expr = str(c.get("id", "?")), str(c.get("pasada", "")).strip(), str(c.get("derivacion", ""))
        if pas == "post":
            crudos = sorted(n for n in RAW_NAMES if _uses(expr, n))
            if crudos:
                bad.append(f"I-2 claim '{cid}' es 'post' pero deriva del corpus CRUDO ({', '.join(crudos)}): "
                           f"contaría los degradados que la SPI sacó")
            elif not any(_uses(expr, n) for n in V2_NAMES):
                bad.append(f"I-2 claim '{cid}' se declara 'post' pero no usa ninguna vista post-SPI "
                           f"({'|'.join(sorted(V2_NAMES))}) — lo dice, no lo hace")
        elif pas == "flujo1":
            v2 = sorted(n for n in (V2_NAMES | {"applied"}) if _uses(expr, n))
            if v2:
                bad.append(f"I-2 claim '{cid}' es 'flujo1' pero usa {', '.join(v2)}: un número del flujo "
                           f"que se mueve con la SPI falsifica lo que la pasada 1 hizo")
        elif pas == "spi" and not any(_uses(expr, n) for n in SPI_NAMES):
            bad.append(f"I-2 claim '{cid}' es 'spi' pero no deriva de la segunda pasada "
                       f"({'|'.join(sorted(SPI_NAMES))})")

    # --- I-3 la SPI está aplicada al corpus, no narrada --------------------------------------------
    intr = u.excluidas & u.digest_raw
    if intr:
        bad.append(f"I-3 {len(intr)} claves que la SPI EXCLUYÓ siguen en digest.jsonl: {sorted(intr)[:3]}")
    blq = u.bloqueados & u.digest_raw
    if blq:
        bad.append(f"I-3 {len(blq)} claves admitidas SIN texto completo entraron al digest "
                   f"(admitir al corpus ≠ admitir al digest): {sorted(blq)[:3]}")

    # --- I-4 nada se borra: los degradados siguen en el corpus, se restan por derivación ------------
    faltan = u.degradadas - u.digest_raw
    if faltan:
        bad.append(f"I-4 {len(faltan)} claves degradadas DESAPARECIERON de digest.jsonl "
                   f"(§3.3: se registran, no se borran): {sorted(faltan)[:3]}")

    # --- I-5 integridad de la fusión y de los conjuntos declarados ---------------------------------
    # (Un «toda clave no degradada sobrevive en digest_v2» sería TAUTOLÓGICO: digest_v2 se construye
    #  justamente así. Lo que sí es falsable es la calidad del DATO que sostiene el colapso.)
    universo = u.extraction_raw | u.admitidas
    huerfanas = {f: i for f, i in u.fusion.items() if i not in universo}
    if huerfanas:
        bad.append(f"I-5 {len(huerfanas)} fusión(es) apuntan a una clave que no está en el corpus "
                   f"(la evidencia se colapsaría hacia la nada): {list(huerfanas.items())[:3]}")
    ambiguas = u.degradadas & (set(u.fusion) | set(u.fusion.values()))
    if ambiguas:
        bad.append(f"I-5 {len(ambiguas)} clave(s) son a la vez degradadas y extremo de una fusión: "
                   f"el colapso queda indefinido — hay que decidirlo a mano: {sorted(ambiguas)[:3]}")
    solapan = u.elegibles & u.bloqueados
    if solapan:
        bad.append(f"I-5 {len(solapan)} clave(s) declaradas a la vez elegibles y bloqueadas: {sorted(solapan)[:3]}")
    fuera = (u.elegibles | u.bloqueados) - u.admitidas
    if fuera:
        bad.append(f"I-5 {len(fuera)} clave(s) elegibles/bloqueadas que la SPI no admitió: {sorted(fuera)[:3]}")

    # --- I-6 valores: lo EMITIDO == la recomputación independiente ---------------------------------
    tex_path = root / "sms-v2/claims.tex"
    emitted: dict[str, str] = {}
    if tex_path.exists():
        emitted = {m.group(1): m.group(2) for m in MACRO_RE.finditer(tex_path.read_text(encoding="utf-8"))}
    else:
        bad.append("I-6 no hay sms-v2/claims.tex emitido (correr verify_sms_claims.py --emit)")

    expected = u.expected()
    for cid, (pas_req, want) in expected.items():
        claim = by_id.get(cid)
        if claim is None:
            bad.append(f"I-6 falta el claim de carga '{cid}' ({pas_req}) — el contrato §4 lo exige")
            continue
        if str(claim.get("pasada", "")).strip() != pas_req:
            bad.append(f"I-6 claim '{cid}' debe ser pasada '{pas_req}'")
        if want is None:
            bad.append(f"I-6 no se pudo recomputar el valor de referencia de '{cid}' "
                       f"(¿AGREEMENT.md sin κ reportado?)")
            continue
        if not emitted:
            continue
        if cid not in emitted:
            bad.append(f"I-6 claim '{cid}' no aparece emitido en claims.tex")
            continue
        try:
            got = _num(emitted[cid])
        except ValueError:
            bad.append(f"I-6 valor emitido de '{cid}' no es numérico: {emitted[cid]!r}")
            continue
        if abs(got - want) > 0.001:
            bad.append(f"I-6 '{cid}' emitido {emitted[cid]} != recomputado {want} "
                       f"(dos implementaciones independientes discrepan: una de las dos miente)")

    # --- I-7 residuo publicado: una amenaza que no se cita no existe -------------------------------
    paper = root / "sms-v2/sms-v2.tex"
    if not paper.exists():
        bad.append("I-7 no hay sms-v2/sms-v2.tex")
    else:
        body = paper.read_text(encoding="utf-8")
        obliga = list(THREAT_MACROS)
        if len(u.pendientes) > 0:
            obliga.append("clPostPendientesDigest")
        for macro in obliga:
            if not re.search(rf"\\{macro}\b", body):
                bad.append(f"I-7 la amenaza declarada \\{macro} no se cita en sms-v2.tex "
                           f"— un residuo que no se imprime está escondido")

    # --- I-8 κ se deriva, no se copia --------------------------------------------------------------
    for cid in ("clFiaKappaColapsado", "clFiaKappaExacto"):
        claim = by_id.get(cid)
        if claim is None:
            continue  # ya reportado por I-6
        expr = str(claim.get("derivacion", ""))
        if NUMLIT_RE.search(expr):
            bad.append(f"I-8 la derivación de '{cid}' contiene un literal numérico: κ se DERIVA de los "
                       f"verdicts (collapse/cohen_kappa), no se copia de AGREEMENT.md")

    if verbose:
        print(f"[universo] digest_v2={len(u.digest_v2)} corpus_v2={len(u.corpus_v2)} "
              f"degradadas={len(u.degradadas)} fusiones={len(u.fusion)} "
              f"pendientes={len(u.pendientes)} bloqueados={len(u.bloqueados)} "
              f"κcol={u.kappa_colapsado} κexa={u.kappa_exacto}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]),
                    help="raíz de research/ (por defecto, la del propio archivo)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    bad = check(Path(args.root), verbose=args.verbose)
    if bad:
        print(f"RED: {len(bad)} invariante(s) rotos — el ledger NO deriva de la SPI aplicada")
        for b in bad:
            print(f"  - {b}")
        return 1
    print("GREEN: claims.yml deriva de la SPI aplicada (I-1..I-8)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
