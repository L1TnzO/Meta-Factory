#!/usr/bin/env python3
"""The anti-invention gate: every number in the SMS v2 is re-derived from the corpus (protocol §9.5).

Trust-chain: written by the orchestrator, by hand. This is the tooth that makes the guía-del-informe rule
(«nunca inventes datos, métricas ni citas») a MACHINE property instead of a promise.

How it works
------------
`sms-v2/claims.yml` holds every quantitative assertion of the paper as `id · pregunta · derivacion ·
unidad · glosa`, where `derivacion` is a Python expression over the COMMITTED corpus artifacts. This gate
re-runs all of them and emits `sms-v2/claims.tex` as `\\newcommand{\\clID}{value}`. The `.tex` never writes
a literal: it writes `\\clID`. Consequence: **a number that no longer follows from the corpus stops
compiling the paper**, and a corpus correction propagates to every sentence that used it.

The five teeth (§9.5), each with an obvious sabotage:
  1. a derivation that raises, or a `claims.tex` that is stale w.r.t. a re-derivation  -> RED
  2. a `\\cl…` macro used in the .tex but never defined                                 -> RED
  3. a claim defined but never used (an orphan number nobody is accountable for)      -> RED
  4. a bare digit inside a `%%CLAIMS-STRICT` region, outside the whitelist            -> RED
  5. a `\\cite{k}` whose key is not in the .bib, or whose .bib entry is not a corpus key -> RED

Usage:
    python3 harvest/verify_sms_claims.py --emit     # re-derive and (re)write claims.tex
    python3 harvest/verify_sms_claims.py            # verify only: claims.tex must already be current
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from closure_law import ROOT, collapse, cohen_kappa  # noqa: E402

SMS_DIR = ROOT / "sms-v2"
CLAIMS_YML = SMS_DIR / "claims.yml"
CLAIMS_TEX = SMS_DIR / "claims.tex"
TEX = SMS_DIR / "sms-v2.tex"
BIB = SMS_DIR / "sms-v2.bib"

ID_RE = re.compile(r"^[A-Za-z]+$")          # LaTeX macro names: letters only
MACRO_RE = re.compile(r"\\(cl[A-Za-z]+)\b")
CITE_RE = re.compile(r"\\cite[tp]?\{([^}]*)\}")
BIBKEY_RE = re.compile(r"^@\w+\{([^,]+),", re.M)
STRICT_OPEN = "%%CLAIMS-STRICT"
STRICT_CLOSE = "%%CLAIMS-STRICT-END"
# Digits that are legitimately literal even inside a strict region.
DIGIT_WHITELIST = re.compile(
    r"(RQ\s?\d)|(§\s?\d[\d.]*)|(\b(19|20)\d\d\b)|(GPT-\d)|(Claude\s?\d)|(Gemini\s?\d)"
    r"|(C[EI]-\s?\d)"          # identificadores de criterio: CE-1, CI-2 -- nombres, no cifras
    r"|(Llama\s?\d)|(\\cl[A-Za-z]+)|(\\ref\{[^}]*\})|(\\label\{[^}]*\})|(\\cite[tp]?\{[^}]*\})"
    r"|(\\includegraphics[^}]*\})"
    # LaTeX lengths are layout, not claims: 1.2em, 0.5\textwidth, 12pt...
    r"|(\d+(\.\d+)?\s*(em|ex|pt|cm|mm|in|bp|sp))"
    r"|(\d*\.?\d+\s*\\(text|column|line|page)width)"
)
BARE_DIGIT = re.compile(r"\d")


# ------------------------------------------------------------------ corpus namespace
def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]



def _quoted(grey_key: str, needle: str) -> str:
    """Devuelve `needle` sólo si aparece LITERALMENTE en la instantánea gris `grey_key`.

    Extiende la ley anti-invención (§9.5) de los agregados a las CITAS. Un número tomado de un
    documento de proveedor no se deriva del corpus: se copia de una fuente. Pero la fuente está
    congelada con sha256, así que la copia SÍ es verificable — y aquí se verifica: si la cadena no
    está en el snapshot, la derivación revienta y el paper no compila. Es la diferencia entre citar
    y afirmar que se citó.
    """
    path = ROOT / f"corpus/grey/{grey_key}.txt"
    if not path.exists():
        raise FileNotFoundError(f"no hay instantánea gris '{grey_key}' (¿se cosechó?)")
    text = path.read_text(encoding="utf-8", errors="replace")
    flat = " ".join(text.split())
    if needle not in flat and needle not in text:
        raise ValueError(f"'{needle}' NO aparece en la instantánea '{grey_key}' — "
                         f"una cita que la fuente no sostiene")
    return needle


def build_namespace() -> dict:
    """Every artifact a claim may derive from. Read-only by construction: plain lists of dicts."""
    spi: list[dict] = []
    spi_dir = ROOT / "corpus/spi/batches"
    if spi_dir.exists():
        for qdir in sorted(p for p in spi_dir.iterdir() if p.is_dir()):
            for path in sorted(qdir.glob("*.verdict.jsonl")):
                for row in _read_jsonl(path):
                    row["_queue"] = qdir.name
                    spi.append(row)
    ns = {
        "sheet_full": _read_csv(ROOT / "corpus/screening/screening_full.csv"),
        "sheet_snowball": _read_csv(ROOT / "corpus/screening/screening_snowball.csv"),
        "extraction": _read_csv(ROOT / "corpus/extraction/extraction.csv"),
        "digest": _read_jsonl(ROOT / "corpus/digestion/digest.jsonl"),
        "corpus": _read_jsonl(ROOT / "corpus/merged/corpus.jsonl"),
        "grey": _read_csv(ROOT / "corpus/grey/manifest.csv"),
        "artifacts": _read_csv(ROOT / "corpus/artifacts.csv"),
        "duplicados": _read_csv(ROOT / "corpus/screening/queues/DUPLICADOS-INCLUIDOS.csv"),
        "spi": spi,
        "conflicts": _read_csv(ROOT / "corpus/spi/CONFLICTOS.csv"),
        "gmdos": (__import__("yaml").safe_load((ROOT / "sms-v2/gmdos-taxonomy.yml").read_text(encoding="utf-8"))
                  if (ROOT / "sms-v2/gmdos-taxonomy.yml").exists() else []),
        # helpers
        "Counter": Counter, "defaultdict": defaultdict, "len": len, "set": set, "sorted": sorted,
        "sum": sum, "min": min, "max": max, "round": round, "abs": abs, "int": int, "float": float,
        "str": str, "list": list, "dict": dict, "any": any, "all": all, "zip": zip, "range": range,
        "collapse": collapse, "cohen_kappa": cohen_kappa,
        "facets": lambda row, field="F": [f for f in (row.get(field) or "").split(";") if f],
        "toks": lambda row, field: [t for t in (row.get(field) or "").replace(",", ";").split(";") if t.strip()],
        "pct": lambda a, b: (100.0 * a / b) if b else 0.0,
        "quoted": _quoted,
    }
    ns["__builtins__"] = {}  # no import, no open, no exec: a ledger derives, it does not act
    return ns


# ------------------------------------------------------------------ formatting
def fmt(value, unidad: str) -> str:
    """Spanish typographic conventions: 1.069 for thousands, 19,7 for decimals."""
    if unidad == "int":
        return f"{int(value):,}".replace(",", ".")
    if unidad == "pct1":
        return f"{float(value):.1f}".replace(".", ",")
    if unidad == "pct0":
        return f"{float(value):.0f}"
    if unidad == "float2":
        return f"{float(value):.2f}".replace(".", ",")
    if unidad == "float3":
        return f"{float(value):.3f}".replace(".", ",")
    if unidad == "raw":
        # Una cita literal puede traer caracteres que LaTeX interpreta ('%' abre comentario y se
        # comería el resto de la línea). Se escapan al emitir, no al citar: el claims.yml conserva
        # la cadena tal como aparece en la fuente, que es lo que `quoted()` verifica.
        out = str(value)
        for ch in ("\\", "&", "%", "$", "#", "_", "{", "}"):
            out = out.replace(ch, "\\" + ch)
        return out
    raise ValueError(f"unknown unidad '{unidad}' (int|pct0|pct1|float2|float3|raw)")


def load_claims() -> list[dict]:
    try:
        import yaml
    except ImportError:
        print("RED: PyYAML not available (needed to read claims.yml)")
        raise SystemExit(1)
    data = yaml.safe_load(CLAIMS_YML.read_text(encoding="utf-8")) or []
    if not isinstance(data, list):
        print("RED: claims.yml must be a LIST of claims")
        raise SystemExit(1)
    return data


def derive_all(claims: list[dict], errors: list[str]) -> dict[str, str]:
    ns = build_namespace()
    values: dict[str, str] = {}
    for c in claims:
        cid = str(c.get("id", "")).strip()
        if not ID_RE.match(cid):
            errors.append(f"claim id '{cid}' must be letters only (it becomes a LaTeX macro name)")
            continue
        if cid in values:
            errors.append(f"claim id '{cid}' declared twice")
            continue
        # `glosa` is optional context; `pregunta` is not — a number whose question nobody wrote down
        # is trivia, and trivia is what pads a results section.
        for field in ("pregunta", "derivacion", "unidad"):
            if not str(c.get(field, "")).strip():
                errors.append(f"claim '{cid}': missing '{field}' (a number without its question is trivia)")
        try:
            # The namespace goes in as GLOBALS, not locals: a comprehension body opens its own frame
            # that can only see globals, so `sum(1 for r in extraction ...)` would otherwise NameError.
            raw = eval(c["derivacion"], ns, {})  # noqa: S307 — committed, hand-reviewed ledger
        except Exception as exc:  # noqa: BLE001
            errors.append(f"claim '{cid}': derivation FAILED — {type(exc).__name__}: {exc}")
            continue
        try:
            values[cid] = fmt(raw, str(c.get("unidad", "")).strip())
        except Exception as exc:  # noqa: BLE001
            errors.append(f"claim '{cid}': cannot format {raw!r} — {exc}")
    return values


def render_tex(claims: list[dict], values: dict[str, str]) -> str:
    out = [
        "% GENERATED by harvest/verify_sms_claims.py — DO NOT EDIT BY HAND.",
        "% Every macro below is re-derived from the committed corpus (protocol §9.5).",
        "% If you want to change a number, change the corpus or the derivation, never this file.",
        "",
    ]
    for c in claims:
        cid = str(c.get("id", "")).strip()
        if cid in values:
            out.append(f"% {cid}: {c.get('pregunta', '')}")
            out.append(f"\\newcommand{{\\{cid}}}{{{values[cid]}}}")
    return "\n".join(out) + "\n"


def strict_regions(tex: str) -> list[tuple[int, str]]:
    """(line number, line) for every line inside a %%CLAIMS-STRICT ... %%CLAIMS-STRICT-END region.

    A `tikzpicture` body is EXEMPT, but not because it is inconvenient: axis bounds, bar widths and
    colour levels are layout, and exempting them wholesale would be a hole only if the plotted DATA
    were also exempt. It is not — `coordinates{...}` is checked separately and harder (see
    `plot_data_problems`), so a figure still cannot state a number the corpus does not derive.
    """
    out: list[tuple[int, str]] = []
    inside = False
    in_tikz = False
    for n, line in enumerate(tex.splitlines(), 1):
        stripped = line.strip()
        if "\\begin{tikzpicture}" in stripped:
            in_tikz = True
        if "\\end{tikzpicture}" in stripped:
            in_tikz = False
            continue
        if stripped.startswith(STRICT_CLOSE):
            inside = False
            continue
        if stripped.startswith(STRICT_OPEN):
            inside = True
            continue
        if inside and not in_tikz and not stripped.startswith("%"):
            out.append((n, line))
    return out


COORDS_RE = re.compile(r"coordinates\s*\{(.*?)\}\s*;", re.S)


def plot_data_problems(tex: str) -> list[str]:
    """Every plotted coordinate must be a claim macro. A chart is an assertion like any sentence."""
    problems: list[str] = []
    for m in COORDS_RE.finditer(tex):
        body = m.group(1)
        scrubbed = re.sub(r"\\cl[A-Za-z]+", "", body)
        digits = "".join(ch for ch in scrubbed if ch.isdigit())
        if digits:
            problems.append(f"plotted coordinate(s) with literal digit(s) '{digits[:20]}' — a chart "
                            f"asserts numbers too; use \\cl macros")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--emit", action="store_true", help="(re)write claims.tex from the derivations")
    ap.add_argument("--draft", action="store_true",
                    help="iteration mode: an unused claim is a WARNING, not RED (the acceptance gate "
                         "never passes --draft, so an orphan number cannot survive to the final paper)")
    args = ap.parse_args()

    errors: list[str] = []
    if not CLAIMS_YML.exists():
        print(f"RED: no claims ledger at {CLAIMS_YML}")
        return 1

    claims = load_claims()
    values = derive_all(claims, errors)

    # ---- tooth 1: claims.tex must be exactly what a fresh derivation produces
    rendered = render_tex(claims, values)
    if args.emit:
        SMS_DIR.mkdir(parents=True, exist_ok=True)
        CLAIMS_TEX.write_text(rendered, encoding="utf-8")
    elif not CLAIMS_TEX.exists():
        errors.append("claims.tex does not exist (run with --emit)")
    elif CLAIMS_TEX.read_text(encoding="utf-8") != rendered:
        errors.append("claims.tex is STALE — it no longer matches a fresh derivation from the corpus")

    if TEX.exists():
        tex = TEX.read_text(encoding="utf-8")
        used = set(MACRO_RE.findall(tex))

        # ---- tooth 2: used but undefined
        for m in sorted(used - set(values)):
            errors.append(f"macro \\{m} used in the paper but no claim defines it")
        # ---- tooth 3: defined but unused
        orphans = sorted(set(values) - used)
        if args.draft:
            if orphans:
                print(f"WARN (draft): {len(orphans)} claim(s) not yet used in the paper")
        else:
            for m in orphans:
                errors.append(f"claim '{m}' is never used in the paper (orphan number — delete it or use it)")

        # ---- tooth 4: bare digits inside strict regions
        for n, line in strict_regions(tex):
            scrubbed = DIGIT_WHITELIST.sub("", line)
            if BARE_DIGIT.search(scrubbed):
                bad = "".join(ch for ch in scrubbed if ch.isdigit())
                errors.append(f"{TEX.name}:{n}: literal digit(s) '{bad}' inside a CLAIMS-STRICT region "
                              f"— every result number must be a \\cl macro")

        # ---- tooth 4b: plotted data must be macros too
        errors.extend(f"{TEX.name}: {p}" for p in plot_data_problems(tex))

        # ---- tooth 5: citations must resolve to the corpus
        if BIB.exists():
            bibkeys = set(BIBKEY_RE.findall(BIB.read_text(encoding="utf-8")))
        else:
            bibkeys = set()
            if CITE_RE.search(tex):
                errors.append("the paper cites but there is no sms-v2.bib")
        cited: set[str] = set()
        for group in CITE_RE.findall(tex):
            cited |= {k.strip() for k in group.split(",") if k.strip()}
        for k in sorted(cited - bibkeys):
            errors.append(f"\\cite{{{k}}} has no entry in sms-v2.bib (a citation that resolves to nothing)")
        ns = build_namespace()
        corpus_keys = ({r["key"] for r in ns["sheet_full"]} | {r["key"] for r in ns["sheet_snowball"]}
                       | {r["key"] for r in ns["grey"]})
        mapped = set()
        if BIB.exists():
            for m in re.finditer(r"^@\w+\{([^,]+),(.*?)^\}", BIB.read_text(encoding="utf-8"),
                                 re.M | re.S):
                entry_key, body = m.group(1), m.group(2)
                found = re.search(r"corpuskey\s*=\s*[{\"]([^}\"]+)", body)
                if found and found.group(1).strip() in corpus_keys:
                    mapped.add(entry_key)
            for k in sorted(cited & bibkeys - mapped):
                errors.append(f"\\cite{{{k}}}: bib entry has no `corpuskey` that exists in the corpus "
                              f"— it was not screened, so it cannot be cited as evidence")
    else:
        if not args.emit:
            errors.append(f"no paper at {TEX}")

    # ---- tooth 6: the G-M2 taxonomy must cover EXACTLY the refutations, no more and no less.
    # A hand-made classification of contested evidence is the easiest place in the whole paper to
    # cherry-pick: drop three inconvenient rows and the headline flips. So it is gated like data.
    tax_path = SMS_DIR / "gmdos-taxonomy.yml"
    if tax_path.exists():
        import yaml
        tax = yaml.safe_load(tax_path.read_text(encoding="utf-8")) or []
        classified = {str(t.get("key", "")).strip() for t in tax}
        ns = build_namespace()
        refuted = {r["key"] for r in ns["digest"]
                   if any(a["postura"] == "REFUTA" and a["ancla"] == "G-M2"
                          for a in r.get("mf_aplicabilidad", []))}
        for k in sorted(refuted - classified):
            errors.append(f"gmdos-taxonomy: {k} refutes G-M2 but is unclassified (silently dropping "
                          f"contested evidence is how a taxonomy lies)")
        for k in sorted(classified - refuted):
            errors.append(f"gmdos-taxonomy: {k} is classified but does not refute G-M2 in the digest")
        for t in tax:
            if not str(t.get("evidencia", "")).strip():
                errors.append(f"gmdos-taxonomy: {t.get('key')} has no cited evidence for its assignment")

    for e in errors:
        print(f"RED: {e}")
    if errors:
        print(f"CLAIMS GATE: RED — {len(errors)} problem(s)")
        return 1
    print(f"CLAIMS GATE: PASS — {len(values)} claim(s) re-derived from the corpus"
          + (f", claims.tex emitted" if args.emit else ", claims.tex current")
          + (f", {len(set(MACRO_RE.findall(TEX.read_text(encoding='utf-8'))))} used in the paper"
             if TEX.exists() else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
