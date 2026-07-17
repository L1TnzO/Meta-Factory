#!/usr/bin/env python3
"""OpenAlex backward/forward snowball harvest, round 1 (SMS-V2-PROTOCOL.md §7.3).

Seven subcommands, run in sequence to build a NOT-already-in-corpus candidate
set from a seed set (v2 INCLUIR works + the 12 gold works), then rank and
enrich it:

  seeds        build the seed set (INCLUIR joined to corpus + gold works).
  resolve      fill in missing OpenAlex work ids for arXiv seeds.
  backward     collect each seed's referenced_works (corpus-local when known,
               else one OpenAlex fetch per seed).
  forward      collect each seed's citing works (OpenAlex, paginated).
  candidates   aggregate backward+forward into a ranked, deduped, NOT-in-corpus
               candidate list.
  enrich       fetch title/doi/year/abstract for candidates from OpenAlex.
  enrich-arxiv fetch title/year/abstract for a list of arXiv ids directly.

Network etiquette (ALL fetching subcommands): a --mailto is appended to every
OpenAlex URL (polite pool), >=0.15s between requests, 30s timeout, one retry
after a 5s backoff on HTTP 429/5xx (then the failure is recorded and the run
continues), User-Agent 'sms-v2-snowball'. Every cache/output file is written
ATOMICALLY (tmp file in the same directory + os.replace) and is RESUMABLE —
each subcommand reads what is already on disk and skips completed work.
Stdlib only.

Usage:
  python3 snowball.py seeds --corpus ../corpus/merged/corpus.jsonl \
      --sheet ../corpus/screening/screening_full.csv --out seeds.csv
  python3 snowball.py resolve --seeds seeds.csv --mailto you@example.org
  python3 snowball.py backward --seeds seeds.csv \
      --corpus ../corpus/merged/corpus.jsonl --cache backward_cache.jsonl
  python3 snowball.py forward --seeds seeds.csv --cache forward_cache.jsonl \
      --mailto you@example.org
  python3 snowball.py candidates --corpus ../corpus/merged/corpus.jsonl \
      --backward-cache backward_cache.jsonl --forward-cache forward_cache.jsonl \
      --out candidates.csv
  python3 snowball.py enrich --candidates candidates.csv \
      --out-jsonl enriched.jsonl --mailto you@example.org --min-total 2
  python3 snowball.py enrich-arxiv --ids 2506.10484,2507.07957 \
      --out-jsonl enriched_arxiv.jsonl
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sanity_check_gold import GOLD  # noqa: E402  (name -> (regex, arxiv_id, need))

USER_AGENT = "sms-v2-snowball"
SLEEP_S = 0.15
TIMEOUT_S = 30
RETRY_BACKOFF_S = 5
PROGRESS_EVERY = 10
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
BATCH_SIZE = 50

ARXIV_DOI_RE = re.compile(r"10\.48550/arxiv\.([^\s]+)", re.IGNORECASE)
DOI_PREFIX_RE = re.compile(r"^https?://doi\.org/", re.IGNORECASE)
VERSION_SUFFIX_RE = re.compile(r"v\d+$", re.IGNORECASE)
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
OPENALEX_PREFIX = "https://openalex.org/"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

CANDIDATE_FIELDS = ["wid", "doi", "year", "title", "backward_n", "forward_n", "total", "seeds_sample"]
SEED_FIELDS = ["seed_key", "origin", "openalex_id", "arxiv_id", "doi", "title"]


# --------------------------------------------------------------------------
# Pure helpers — identity normalization, no I/O
# --------------------------------------------------------------------------

def vstrip(arxiv_id: str) -> str:
    """Strip a trailing version suffix ('v2') from an arXiv id."""
    return VERSION_SUFFIX_RE.sub("", (arxiv_id or "").strip())


def normalize_doi(doi: str) -> str:
    doi = (doi or "").strip()
    doi = DOI_PREFIX_RE.sub("", doi)
    return doi.lower()


def normalize_title(title: str) -> str:
    t = NON_ALNUM_RE.sub(" ", (title or "").lower())
    return t.strip()


def extract_wid(openalex_id_or_url: str) -> str:
    """Trailing OpenAlex work id ('W123...') from an 'id' field, or '' if the
    value is not an https://openalex.org/... URL (e.g. an arXiv-sourced
    record whose 'id' is an arxiv.org URL has no OpenAlex identity)."""
    s = (openalex_id_or_url or "").strip()
    if s.startswith(OPENALEX_PREFIX):
        return s[len(OPENALEX_PREFIX):]
    return ""


def record_key(rec: dict) -> str:
    """Mirrors research/harvest/download_pdfs.py:record_key() EXACTLY."""
    for candidate in (rec.get("id"), rec.get("doi"), rec.get("arxiv_id"), rec.get("title")):
        if candidate:
            return re.sub(r"[^A-Za-z0-9._-]+", "_", str(candidate).split("/")[-1])[:120]
    return "unknown"


def reconstruct_abstract(inverted_index: dict) -> str:
    """OpenAlex 'abstract_inverted_index' (word -> [positions]) -> plain text,
    position-sorted. {'Hello': [0], 'world': [1]} -> 'Hello world'."""
    if not inverted_index:
        return ""
    positions = []
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort(key=lambda p: p[0])
    return " ".join(w for _, w in positions)


def iter_batches(seq, n):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


# --------------------------------------------------------------------------
# I/O helpers
# --------------------------------------------------------------------------

def load_jsonl(path: Path) -> list:
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def load_csv_rows(path: Path) -> list:
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def atomic_write_text(path: Path, text: str) -> None:
    """Write tmp file in the same dir, then os.replace — no partial writes
    are ever visible under the target path, and no tmp file survives."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.tmp"
    tmp.write_text(text, encoding="utf-8")
    os.replace(str(tmp), str(path))


def atomic_write_csv(path: Path, fieldnames: list, rows: list) -> None:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    atomic_write_text(path, buf.getvalue())


def atomic_write_jsonl(path: Path, rows: list) -> None:
    text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    atomic_write_text(path, text)


def _progress(tag: str, count: int) -> None:
    if count % PROGRESS_EVERY == 0:
        print(f"[snowball] {tag}: {count} requests...", file=sys.stderr)


def _http_get_json(url: str, mailto: str = "") -> dict:
    """GET url (OpenAlex convention: JSON body), politely. One retry after a
    5s backoff on 429/5xx; any other error propagates to the caller, which
    is responsible for recording the failure and continuing the batch."""
    full_url = url
    if mailto:
        sep = "&" if "?" in url else "?"
        full_url = f"{url}{sep}mailto={urllib.parse.quote(mailto)}"
    req = urllib.request.Request(full_url, headers={"User-Agent": USER_AGENT})
    attempt = 0
    while True:
        attempt += 1
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                data = resp.read()
            return json.loads(data.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in RETRYABLE_STATUS and attempt < 2:
                time.sleep(RETRY_BACKOFF_S)
                continue
            raise


# --------------------------------------------------------------------------
# Pure logic — seeds join
# --------------------------------------------------------------------------

def build_seed_rows(corpus_records: list, sheet_rows: list, gold: dict) -> list:
    """Seed set = every sheet row with decision==INCLUIR joined to the corpus
    via record_key() (origin='included'), PLUS one row per GOLD work
    (origin='gold', seed_key=the gold arXiv id — gold works are seeds by
    protocol §7.3 regardless of corpus presence)."""
    corpus_by_key = {record_key(rec): rec for rec in corpus_records}
    rows = []
    for srow in sheet_rows:
        if (srow.get("decision") or "").strip() != "INCLUIR":
            continue
        key = srow.get("key") or ""
        rec = corpus_by_key.get(key)
        if rec is None:
            continue
        rows.append({
            "seed_key": key,
            "origin": "included",
            "openalex_id": extract_wid(rec.get("id")),
            "arxiv_id": rec.get("arxiv_id") or "",
            "doi": rec.get("doi") or "",
            "title": rec.get("title") or "",
        })
    for name, (_pattern, arxiv_id, _need) in gold.items():
        rows.append({
            "seed_key": arxiv_id,
            "origin": "gold",
            "openalex_id": "",
            "arxiv_id": arxiv_id,
            "doi": "",
            "title": name,
        })
    return rows


# --------------------------------------------------------------------------
# Pure logic — candidate identity / dedup / aggregation
# --------------------------------------------------------------------------

def build_corpus_identity_set(corpus_records: list) -> set:
    """Every identity a corpus record is known by: (wid), (doi), (arxiv id),
    (normalized title). A candidate sharing ANY one of these with the corpus
    is already in the corpus and must be excluded."""
    idset = set()
    for rec in corpus_records:
        wid = extract_wid(rec.get("id"))
        if wid:
            idset.add(("wid", wid))
        doi = normalize_doi(rec.get("doi"))
        if doi:
            idset.add(("doi", doi))
        aid = vstrip(rec.get("arxiv_id") or "")
        if aid:
            idset.add(("arxiv", aid.lower()))
        title = normalize_title(rec.get("title"))
        if title:
            idset.add(("title", title))
    return idset


def candidate_identities(wid: str = "", doi: str = "", arxiv_id: str = "", title: str = "") -> list:
    ids = []
    if wid:
        ids.append(("wid", wid))
    ndoi = normalize_doi(doi)
    if ndoi:
        ids.append(("doi", ndoi))
    if arxiv_id:
        ids.append(("arxiv", vstrip(arxiv_id).lower()))
    ntitle = normalize_title(title)
    if ntitle:
        ids.append(("title", ntitle))
    return ids


def is_excluded(identities: list, corpus_set: set) -> bool:
    return any(i in corpus_set for i in identities)


def aggregate_candidates(corpus_records: list, backward_rows: list, forward_rows: list) -> list:
    """Build the ranked, deduped, NOT-in-corpus candidate list from the
    backward cache ({"seed","wid","referenced_works":[urls]}) and the forward
    cache ({"seed","wid","citing":[work objects]}). backward_n/forward_n
    count DISTINCT seeds; pure-backward candidates carry no doi/title/year
    (only forward's citing work objects carry metadata) until 'enrich'."""
    corpus_set = build_corpus_identity_set(corpus_records)
    agg: dict = {}

    def entry(wid: str) -> dict:
        return agg.setdefault(wid, {
            "backward_seeds": set(), "forward_seeds": set(),
            "doi": "", "title": "", "year": "",
        })

    for row in backward_rows:
        seed = row.get("seed", "")
        for url in row.get("referenced_works") or []:
            wid = extract_wid(url)
            if not wid:
                continue
            entry(wid)["backward_seeds"].add(seed)

    for row in forward_rows:
        seed = row.get("seed", "")
        for work in row.get("citing") or []:
            wid = extract_wid(work.get("id"))
            if not wid:
                continue
            e = entry(wid)
            e["forward_seeds"].add(seed)
            if not e["doi"] and work.get("doi"):
                e["doi"] = work.get("doi")
            if not e["title"] and work.get("title"):
                e["title"] = work.get("title")
            if not e["year"] and work.get("publication_year"):
                e["year"] = work.get("publication_year")

    rows = []
    for wid, data in agg.items():
        identities = candidate_identities(wid=wid, doi=data["doi"], title=data["title"])
        if is_excluded(identities, corpus_set):
            continue
        backward_n = len(data["backward_seeds"])
        forward_n = len(data["forward_seeds"])
        seeds_sample = ";".join(sorted(data["backward_seeds"] | data["forward_seeds"])[:5])
        rows.append({
            "wid": wid, "doi": data["doi"], "year": data["year"], "title": data["title"],
            "backward_n": backward_n, "forward_n": forward_n,
            "total": backward_n + forward_n, "seeds_sample": seeds_sample,
        })
    rows.sort(key=lambda r: (-r["total"], r["wid"]))
    return rows


# --------------------------------------------------------------------------
# Subcommands
# --------------------------------------------------------------------------

def cmd_seeds(args) -> int:
    corpus = load_jsonl(args.corpus)
    sheet = load_csv_rows(args.sheet)
    rows = build_seed_rows(corpus, sheet, GOLD)
    atomic_write_csv(args.out, SEED_FIELDS, rows)
    n_gold = sum(1 for r in rows if r["origin"] == "gold")
    print(f"seeds: {len(rows)} total ({len(rows) - n_gold} included, {n_gold} gold)")
    return 0


def cmd_resolve(args) -> int:
    rows = load_csv_rows(args.seeds)
    need = [r for r in rows if not (r.get("openalex_id") or "") and (r.get("arxiv_id") or "")]
    by_arxiv: dict = {}
    for r in need:
        by_arxiv.setdefault(vstrip(r["arxiv_id"]).lower(), []).append(r)

    req_count = 0
    for batch in iter_batches(sorted(by_arxiv), BATCH_SIZE):
        filt = "|".join(f"10.48550/arxiv.{aid}" for aid in batch)
        url = "https://api.openalex.org/works?filter=doi:" + urllib.parse.quote(filt, safe="|.:") \
            + "&select=id,doi&per-page=50"
        req_count += 1
        try:
            data = _http_get_json(url, args.mailto)
        except Exception as exc:  # noqa: BLE001 — record and continue
            print(f"[snowball] resolve batch failed: {exc}", file=sys.stderr)
            data = {}
        for item in data.get("results", []) or []:
            m = ARXIV_DOI_RE.search(normalize_doi(item.get("doi")))
            if not m:
                continue
            aid = vstrip(m.group(1)).lower()
            for r in by_arxiv.get(aid, []):
                r["openalex_id"] = extract_wid(item.get("id"))
        _progress("resolve", req_count)
        time.sleep(SLEEP_S)

    resolved = sum(1 for r in need if r.get("openalex_id"))
    unresolved = len(need) - resolved
    atomic_write_csv(args.seeds, SEED_FIELDS, rows)
    print(f"resolved {resolved}, unresolved {unresolved}")
    return 0


def cmd_backward(args) -> int:
    seeds = load_csv_rows(args.seeds)
    corpus = load_jsonl(args.corpus)
    corpus_by_wid = {extract_wid(r.get("id")): r for r in corpus if extract_wid(r.get("id"))}
    cache = load_jsonl(args.cache)
    done_wids = {row.get("wid") for row in cache}

    req_count = 0
    for row in seeds:
        wid = row.get("openalex_id") or ""
        if not wid or wid in done_wids:
            continue
        rec = corpus_by_wid.get(wid)
        if rec is not None and rec.get("referenced_works"):
            refs = rec["referenced_works"]
        else:
            req_count += 1
            url = f"https://api.openalex.org/works?filter=openalex:{wid}&select=id,referenced_works&per-page=50"
            try:
                data = _http_get_json(url, getattr(args, "mailto", "") or "")
                results = data.get("results", []) or []
                refs = results[0].get("referenced_works", []) if results else []
            except Exception as exc:  # noqa: BLE001 — record and continue
                print(f"[snowball] backward fetch failed for {wid}: {exc}", file=sys.stderr)
                refs = []
            _progress("backward", req_count)
            time.sleep(SLEEP_S)
        cache.append({"seed": row.get("seed_key", ""), "wid": wid, "referenced_works": refs})
        done_wids.add(wid)
        atomic_write_jsonl(args.cache, cache)

    print(f"backward: {len(cache)} seeds cached")
    return 0


def cmd_forward(args) -> int:
    seeds = load_csv_rows(args.seeds)
    cache = load_jsonl(args.cache)
    done_wids = {row.get("wid") for row in cache}

    req_count = 0
    for row in seeds:
        wid = row.get("openalex_id") or ""
        if not wid or wid in done_wids:
            continue
        citing = []
        cursor = "*"
        while cursor:
            url = (f"https://api.openalex.org/works?filter=cites:{wid}"
                   f"&select=id,doi,title,publication_year,cited_by_count"
                   f"&per-page=200&cursor={urllib.parse.quote(cursor)}")
            req_count += 1
            try:
                data = _http_get_json(url, args.mailto)
            except Exception as exc:  # noqa: BLE001 — record and continue
                print(f"[snowball] forward fetch failed for {wid}: {exc}", file=sys.stderr)
                break
            citing.extend(data.get("results", []) or [])
            cursor = (data.get("meta") or {}).get("next_cursor") or ""
            _progress("forward", req_count)
            time.sleep(SLEEP_S)
        cache.append({"seed": row.get("seed_key", ""), "wid": wid, "citing": citing})
        done_wids.add(wid)
        atomic_write_jsonl(args.cache, cache)

    print(f"forward: {len(cache)} seeds cached")
    return 0


def cmd_candidates(args) -> int:
    corpus = load_jsonl(args.corpus)
    backward_rows = load_jsonl(args.backward_cache)
    forward_rows = load_jsonl(args.forward_cache)
    rows = aggregate_candidates(corpus, backward_rows, forward_rows)
    atomic_write_csv(args.out, CANDIDATE_FIELDS, rows)
    n_ge2 = sum(1 for r in rows if r["total"] >= 2)
    n_ge3 = sum(1 for r in rows if r["total"] >= 3)
    print(f"candidates: {len(rows)} distinct, {n_ge2} with total>=2, {n_ge3} with total>=3")
    return 0


def cmd_enrich(args) -> int:
    cand_rows = load_csv_rows(args.candidates)
    existing = load_jsonl(args.out_jsonl)
    done_keys = {r.get("key") for r in existing}
    targets = [r for r in cand_rows
               if r.get("wid") not in done_keys and int(r.get("total") or 0) >= args.min_total]

    req_count = 0
    updated: dict = {}
    for batch in iter_batches(targets, BATCH_SIZE):
        ids = "|".join(r["wid"] for r in batch)
        url = ("https://api.openalex.org/works?filter=openalex:" + ids
               + "&select=id,doi,title,publication_year,type,language,abstract_inverted_index&per-page=50")
        req_count += 1
        try:
            data = _http_get_json(url, args.mailto)
        except Exception as exc:  # noqa: BLE001 — record and continue
            print(f"[snowball] enrich batch failed: {exc}", file=sys.stderr)
            data = {}
        for item in data.get("results", []) or []:
            wid = extract_wid(item.get("id"))
            if not wid:
                continue
            abstract = reconstruct_abstract(item.get("abstract_inverted_index") or {})
            existing.append({
                "key": wid, "source": "openalex",
                "doi": item.get("doi") or "", "title": item.get("title") or "",
                "year": item.get("publication_year"), "type": item.get("type") or "",
                "language": item.get("language") or "", "abstract": abstract,
            })
            updated[wid] = {
                "title": item.get("title") or "", "doi": item.get("doi") or "",
                "year": item.get("publication_year") or "",
            }
        _progress("enrich", req_count)
        time.sleep(SLEEP_S)

    atomic_write_jsonl(args.out_jsonl, existing)
    for row in cand_rows:
        if row.get("wid") in updated:
            row.update(updated[row["wid"]])
    atomic_write_csv(args.candidates, CANDIDATE_FIELDS, cand_rows)
    print(f"enrich: {len(updated)} enriched, {len(existing)} total in {args.out_jsonl}")
    return 0


def cmd_enrich_arxiv(args) -> int:
    ids = [i.strip() for i in args.ids.split(",") if i.strip()]
    existing = load_jsonl(args.out_jsonl)
    done_keys = {r.get("key") for r in existing}
    todo = [i for i in ids if vstrip(i) not in done_keys]
    if not todo:
        print("enrich-arxiv: 0 fetched, already cached")
        return 0

    id_list = ",".join(todo)
    url = f"https://export.arxiv.org/api/query?id_list={urllib.parse.quote(id_list)}&max_results={len(todo)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        raw = resp.read()
    root = ET.fromstring(raw)

    n = 0
    for entry_el in root.findall("atom:entry", ATOM_NS):
        id_url = (entry_el.findtext("atom:id", default="", namespaces=ATOM_NS) or "").strip()
        aid = vstrip(id_url.rsplit("/", 1)[-1])
        title = re.sub(r"\s+", " ", (entry_el.findtext("atom:title", default="", namespaces=ATOM_NS) or "").strip())
        summary = re.sub(r"\s+", " ", (entry_el.findtext("atom:summary", default="", namespaces=ATOM_NS) or "").strip())
        published = entry_el.findtext("atom:published", default="", namespaces=ATOM_NS) or ""
        existing.append({
            "key": aid, "source": "arxiv", "title": title,
            "year": published[:4] if published else "", "abstract": summary,
        })
        n += 1
    atomic_write_jsonl(args.out_jsonl, existing)
    print(f"enrich-arxiv: {n} fetched, {len(existing)} total in {args.out_jsonl}")
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("seeds", help="build the seed set (INCLUIR + gold)")
    p.add_argument("--corpus", required=True, type=Path)
    p.add_argument("--sheet", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.set_defaults(func=cmd_seeds)

    p = sub.add_parser("resolve", help="fill missing OpenAlex ids for arXiv seeds")
    p.add_argument("--seeds", required=True, type=Path)
    p.add_argument("--mailto", required=True)
    p.set_defaults(func=cmd_resolve)

    p = sub.add_parser("backward", help="collect each seed's referenced_works")
    p.add_argument("--seeds", required=True, type=Path)
    p.add_argument("--corpus", required=True, type=Path)
    p.add_argument("--cache", required=True, type=Path)
    p.add_argument("--mailto", default="")
    p.set_defaults(func=cmd_backward)

    p = sub.add_parser("forward", help="collect each seed's citing works")
    p.add_argument("--seeds", required=True, type=Path)
    p.add_argument("--cache", required=True, type=Path)
    p.add_argument("--mailto", required=True)
    p.set_defaults(func=cmd_forward)

    p = sub.add_parser("candidates", help="aggregate backward+forward into a ranked candidate list")
    p.add_argument("--corpus", required=True, type=Path)
    p.add_argument("--backward-cache", required=True, type=Path, dest="backward_cache")
    p.add_argument("--forward-cache", required=True, type=Path, dest="forward_cache")
    p.add_argument("--out", required=True, type=Path)
    p.set_defaults(func=cmd_candidates)

    p = sub.add_parser("enrich", help="fetch metadata for candidates from OpenAlex")
    p.add_argument("--candidates", required=True, type=Path)
    p.add_argument("--out-jsonl", required=True, type=Path, dest="out_jsonl")
    p.add_argument("--mailto", required=True)
    p.add_argument("--min-total", type=int, default=1, dest="min_total")
    p.set_defaults(func=cmd_enrich)

    p = sub.add_parser("enrich-arxiv", help="fetch metadata for a list of arXiv ids")
    p.add_argument("--ids", required=True)
    p.add_argument("--out-jsonl", required=True, type=Path, dest="out_jsonl")
    p.set_defaults(func=cmd_enrich_arxiv)

    return ap


def main(argv: list | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
