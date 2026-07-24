#!/usr/bin/env python3
"""Genera `sms-v2/sms-v2.bib` DESDE el corpus — la bibliografía no se escribe, se deriva (§9.5).

Trust-chain: escrito a mano. Es la pieza que vuelve imposible la cita alucinada, no por disciplina
sino por construcción: una entrada `.bib` sólo existe si su `corpuskey` es una clave que el cribado
efectivamente decidió. Si el artículo cita algo que nadie cribó, no hay entrada, y el gate de claims
(diente 5) tumba la compilación.

Fuentes de metadatos, en orden de preferencia: `corpus/merged/corpus.jsonl` (cosecha académica) →
`corpus/seeds/snowball-enriched.jsonl` (candidatos de snowball) → las hojas de cribado (título/año,
lo mínimo) → `corpus/grey/manifest.csv` (literatura gris, como `@misc` con fecha de acceso).

Uso:
    python3 harvest/make_bib.py            # lee las \\cite del .tex y emite sólo lo citado
    python3 harvest/make_bib.py --index    # además escribe CITEKEYS.md (índice para redactar)
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from closure_law import ROOT, bibkey  # noqa: E402

SMS_DIR = ROOT / "sms-v2"
TEX = SMS_DIR / "sms-v2.tex"
BIB = SMS_DIR / "sms-v2.bib"
INDEX = SMS_DIR / "CITEKEYS.md"
CITE_RE = re.compile(r"\\cite[tp]?\{([^}]*)\}")


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def escape(text: str) -> str:
    """LaTeX-escape a metadata string. Titles from aggregators carry &, %, _ and stray HTML."""
    text = re.sub(r"<[^>]+>", "", text or "")
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    for ch in ("\\", "{", "}"):
        text = text.replace(ch, "")
    for ch in ("&", "%", "$", "#", "_"):
        text = text.replace(ch, "\\" + ch)
    return " ".join(text.split())


NON_LATIN = re.compile(r"[^\x00-\x7F\u00C0-\u024F\u2010-\u2019\s]")


def digest_authors() -> dict[str, str]:
    """corpus key -> el fragmento de autoría de la `cita` de la digestión ('Deng (2026). Titulo.').

    Se usa SÓLO como respaldo cuando el nombre que devuelve el agregador viene en un sistema de
    escritura que pdflatex no compone (CJK). No se translitera ni se inventa: se toma la forma
    romanizada que ya consta en el corpus, y el respaldo queda documentado aquí para que se pueda
    auditar por qué una entrada difiere del agregador.
    """
    out: dict[str, str] = {}
    for rec in _jsonl(ROOT / "corpus/digestion/digest.jsonl"):
        cita = (rec.get("cita") or "").strip()
        head = re.split(r"\s*\(\d{4}", cita)[0].strip(" .")
        if head:
            out[rec["key"]] = head
    return out


def authors_field(raw) -> str:
    if isinstance(raw, list):
        names = [str(a) for a in raw if a]
    else:
        names = [a.strip() for a in str(raw or "").split(";") if a.strip()]
    if not names:
        return ""
    if len(names) > 12:                      # BibTeX convention, not truncation of evidence
        return escape(names[0]) + " and others"
    return " and ".join(escape(n) for n in names)


def build_index() -> dict[str, dict]:
    """corpus key -> best available metadata."""
    idx: dict[str, dict] = {}

    for row in _csv(ROOT / "corpus/screening/screening_full.csv") + \
               _csv(ROOT / "corpus/screening/screening_snowball.csv"):
        key = row["key"]
        idx.setdefault(key, {}).update({
            "key": key, "title": row.get("title", ""), "year": row.get("year", ""),
            "doi": row.get("doi", ""), "venue": row.get("venue", ""),
            "decision": row.get("decision", ""), "source": "sheet",
        })

    for rec in _jsonl(ROOT / "corpus/merged/corpus.jsonl") + \
               _jsonl(ROOT / "corpus/seeds/snowball-enriched.jsonl"):
        key = (rec.get("id") or "").rsplit("/", 1)[-1] or rec.get("key", "")
        if not key:
            continue
        cur = idx.setdefault(key, {"key": key, "decision": "", "source": "corpus"})
        for field in ("title", "year", "venue", "doi", "type", "arxiv_id", "authors", "oa_url"):
            if rec.get(field) and not cur.get(field):
                cur[field] = rec[field]
    return idx


def grey_index() -> dict[str, dict]:
    return {r["key"]: r for r in _csv(ROOT / "corpus/grey/manifest.csv")}


def entry(meta: dict) -> str:
    key = meta["key"]
    title = escape(meta.get("title") or key)
    year = str(meta.get("year") or "").strip() or "s.f."
    auth = authors_field(meta.get("authors"))
    if auth and NON_LATIN.search(auth):
        fallback = meta.get("_digest_authors") or ""
        print(f"[bib] {key}: autoría no componible por pdflatex "
              f"({'sin respaldo en el digest' if not fallback else 'usando la forma del digest'})")
        auth = escape(fallback)
    venue = escape(meta.get("venue") or "")
    # Normalización cosmética, no de contenido: OpenAlex etiqueta los preprints de arXiv como
    # "arXiv (Cornell University)", que en una bibliografía IEEE se lee como un journal inexistente.
    if "arxiv" in venue.lower():
        venue = "arXiv preprint"
    doi = str(meta.get("doi") or "").replace("https://doi.org/", "").strip()
    arxiv = str(meta.get("arxiv_id") or "").strip()
    kind = "@article" if venue else "@misc"

    lines = [f"{kind}{{{bibkey(key)},"]
    lines.append(f"  title = {{{title}}},")
    if auth:
        lines.append(f"  author = {{{auth}}},")
    lines.append(f"  year = {{{year}}},")
    if venue:
        lines.append(f"  journal = {{{venue}}},")
    if doi:
        lines.append(f"  doi = {{{doi}}},")
    if arxiv:
        lines.append(f"  eprint = {{{arxiv}}},")
        lines.append("  archivePrefix = {arXiv},")
    lines.append(f"  corpuskey = {{{key}}},")   # <- lo que el gate exige y verifica
    lines.append("}")
    return "\n".join(lines)


def grey_entry(row: dict) -> str:
    lines = [f"@misc{{{bibkey(row['key'])},"]
    lines.append(f"  title = {{{escape(row.get('title', ''))}}},")
    lines.append(f"  author = {{{{{escape(row.get('org', ''))}}}}},")
    lines.append(f"  year = {{{(row.get('retrieved_at') or '')[:4]}}},")
    lines.append(f"  howpublished = {{\\url{{{row.get('url', '')}}}}},")
    lines.append(f"  note = {{Documentación técnica de primera mano; consultado el "
                 f"{row.get('retrieved_at', '')}; sha256 {(row.get('sha256') or '')[:16]}}},")
    lines.append(f"  corpuskey = {{{row['key']}}},")
    lines.append("}")
    return "\n".join(lines)


CITE_CACHE = ROOT / "corpus/seeds/cite-enriched.jsonl"


def enrich(keys: list[str]) -> None:
    """Trae autores/venue de OpenAlex SÓLO para lo citado y los cachea en el repo.

    Se cachea a propósito: tras la primera corrida la bibliografía se re-deriva sin red, que es
    condición para que un tercero pueda recompilar el artículo. La red es una conveniencia de
    construcción, nunca una dependencia de verificación.
    """
    import urllib.request

    cached = {r["key"] for r in _jsonl(CITE_CACHE)}
    todo = [k for k in keys if k not in cached and k.startswith("W")]
    if not todo:
        return
    print(f"[bib] enriqueciendo {len(todo)} cita(s) desde OpenAlex…")
    got = []
    for key in todo:
        url = (f"https://api.openalex.org/works/{key}"
               f"?select=id,title,authorships,publication_year,primary_location,doi"
               f"&mailto=catalinalazolocky@gmail.com")
        try:
            with urllib.request.urlopen(url, timeout=30) as fh:
                d = json.loads(fh.read().decode())
        except Exception as exc:  # noqa: BLE001 — una cita sin autor es peor que un aviso
            print(f"[bib] AVISO: {key} no se pudo enriquecer ({type(exc).__name__})")
            continue
        loc = d.get("primary_location") or {}
        src = loc.get("source") or {}
        got.append({
            "key": key,
            "authors": [a.get("author", {}).get("display_name", "")
                        for a in (d.get("authorships") or [])],
            "venue": src.get("display_name") or "",
            "year": d.get("publication_year") or "",
        })
    if got:
        with CITE_CACHE.open("a", encoding="utf-8") as fh:
            for row in got:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"[bib] cacheadas {len(got)} en {CITE_CACHE.name} (committear: re-derivable sin red)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", action="store_true", help="escribe también CITEKEYS.md")
    ap.add_argument("--enrich", action="store_true",
                    help="consulta OpenAlex por autores/venue de lo citado y cachea el resultado")
    args = ap.parse_args()

    idx, grey = build_index(), grey_index()

    cited: set[str] = set()
    if TEX.exists():
        for group in CITE_RE.findall(TEX.read_text(encoding="utf-8")):
            cited |= {k.strip() for k in group.split(",") if k.strip()}

    by_bibkey = {bibkey(k): k for k in list(idx) + list(grey)}
    unknown = sorted(k for k in cited if k not in by_bibkey)

    if args.enrich:
        enrich([by_bibkey[c] for c in cited if c in by_bibkey])
    dauth = digest_authors()
    for k, v in dauth.items():
        if k in idx:
            idx[k]["_digest_authors"] = v
    for row in _jsonl(CITE_CACHE):              # el caché manda sobre las hojas: trae autoría
        if row["key"] in idx:
            for field in ("authors", "venue", "year"):
                if row.get(field):
                    idx[row["key"]][field] = row[field]

    out = ["% GENERADO por harvest/make_bib.py desde el corpus — NO editar a mano.",
           "% Cada entrada lleva `corpuskey`: la clave del registro efectivamente cribado.", ""]
    written = 0
    for ck in sorted(cited):
        if ck in unknown:
            continue
        key = by_bibkey[ck]
        out.append(grey_entry(grey[key]) if key in grey else entry(idx[key]))
        out.append("")
        written += 1

    SMS_DIR.mkdir(parents=True, exist_ok=True)
    BIB.write_text("\n".join(out), encoding="utf-8")
    print(f"[bib] {written} entrada(s) escritas en {BIB.name} desde {len(cited)} cita(s)")
    for k in unknown:
        print(f"[bib] AVISO: \\cite{{{k}}} no corresponde a ninguna clave del corpus — "
              f"el gate de claims lo rechazará (y hace bien)")

    if args.index:
        rows = [m for m in idx.values()
                if (m.get("decision") or "").upper().startswith("INCLUIR") and m.get("title")]
        rows.sort(key=lambda m: (str(m.get("year") or ""), m.get("title", "")), reverse=True)
        lines = ["# CITEKEYS — índice para redactar (GENERADO por make_bib.py)", "",
                 "Clave de cita ← clave del corpus. Sólo aparecen registros INCLUIDOS: citar algo",
                 "no incluido es, por diseño, imposible.", "",
                 "| \\cite{...} | clave corpus | año | título |", "| --- | --- | --- | --- |"]
        for m in rows:
            t = (m.get("title") or "")[:80].replace("|", "/")
            lines.append(f"| `{bibkey(m['key'])}` | `{m['key']}` | {m.get('year','')} | {t} |")
        for k, g in sorted(grey.items()):
            lines.append(f"| `{bibkey(k)}` | `{k}` | gris | {g.get('title','')[:80]} |")
        INDEX.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[bib] índice: {INDEX.name} ({len(rows)} incluidos + {len(grey)} grises)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
