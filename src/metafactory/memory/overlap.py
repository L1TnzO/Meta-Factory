"""overlap (ADR-019 §5/§Consecuencias, M6) — the OBSERVER of the THIRD memory: the harness
auto-memory note-store (`~/.claude/projects/<slug>/memory/*.md` + `MEMORY.md`).

It measures, deterministically and with ZERO model (ADR-008), how much each note DUPLICATES the
`docs/` wiki — the single-source-of-truth for project FACTS (ADR-007 regla 3, the rule M6 declares).
High duplication = the note re-narrates what `docs/` already records = a THIRD drift surface that
should be a POINTER, not a copy (and which the harness's own memory protocol forbids: "don't save
what the repo already records").

Why this is an OBSERVER, not a `meta check` gate (contrast M1's `state_snapshot`, which governs the
IN-tree STATE.md and IS a gate): the auto-memory lives OUTSIDE the git tree, is user-/machine-specific,
and is ABSENT on a clean clone. Wiring it into `meta check` would make the portable, clean-clone-green
proof depend on a path that may not exist. So M6's governance is the single-source RULE (declared in
`reference/MEMORY-ARCHITECTURE.md`) + this re-derivable on-demand measurement — not a tooth. It degrades
gracefully (returns "absent") when the note-store isn't present, so `meta metrics --overlap` stays
portable.

Metric: shingle (k-word n-gram) CONTAINMENT of a note in the `docs/` corpus —
`|note∩docs| / |note|`, not symmetric Jaccard. We ask "how much of the NOTE is already in docs", not
"how similar are the corpora" (`docs/` is ~100× bigger; Jaccard would be dominated by the size gap).
Deterministic: lowercased, whitespace-folded, word-tokenized. It catches LITERAL duplication (the
copy-paste drift surface), not paraphrase; the principled axis is the note's frontmatter `type`
(`feedback`/`reference` = auto-memory's legitimate single-source · `project` = the at-risk narrator).
"""
from __future__ import annotations

import re
from pathlib import Path

# k-word shingle: long enough that incidental word-overlap (shared vocabulary) doesn't register as
# duplication, short enough to catch a copied sentence. 5 is the standard near-duplicate window.
SHINGLE_K = 5

# Containment bands. HIGH = the note is largely already in docs/ → degrade to a pointer. LOW = unique
# relationship/lesson content (auto-memory's legitimate single-source) → keep. MID = partial overlap.
BAND_HIGH = 0.45
BAND_LOW = 0.15

# The per-session FIXED cost: MEMORY.md is injected at every SessionStart. Budget mirrors STATE's
# snapshot discipline (ADR-019 §3) — a gauge for the readout, not a gate (the file is out-of-tree).
MEMORY_INDEX_BUDGET_TOKENS = 4000
_CHARS_PER_TOKEN = 4

_WORD_RE = re.compile(r"\w+", re.UNICODE)
_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)


# ── locating the note-store (best-effort; absent → None, the portable path) ───
def _slug_for(root: Path) -> str:
    """The harness encodes a project's abspath into its note-store dir name by replacing every
    non-ASCII-alphanumeric char with '-' (e.g. `/home/e/Integración` → `-home-e-Integraci-n`)."""
    return "".join(c if (c.isascii() and c.isalnum()) else "-" for c in str(root))


def find_memdir(root: Path, explicit: str | None = None) -> Path | None:
    """Locate the auto-memory note-store for this project, or None if not present on this machine.
    Order: explicit override → slug-derived path → glob fallback by basename. None is normal (clean
    clone / CI / different user) and the readout handles it — never raises."""
    if explicit:
        p = Path(explicit).expanduser()
        return p if (p / "MEMORY.md").exists() else None
    home = Path.home()
    cand = home / ".claude" / "projects" / _slug_for(root.resolve()) / "memory"
    if (cand / "MEMORY.md").exists():
        return cand
    # Fallback: the slug encoding may drift across harness versions; match by the project basename.
    base = "".join(c if (c.isascii() and c.isalnum()) else "-" for c in root.name)
    try:
        for mem in (home / ".claude" / "projects").glob(f"*{base}*/memory/MEMORY.md"):
            return mem.parent
    except OSError:
        pass
    return None


# ── shingles ──────────────────────────────────────────────────────────────────
def _strip_frontmatter(text: str) -> str:
    return _FRONTMATTER_RE.sub("", text, count=1)


def shingles(text: str, k: int = SHINGLE_K) -> set[str]:
    """Set of k-word n-grams over the lowercased, word-tokenized text. Empty if fewer than k words."""
    words = _WORD_RE.findall(text.lower())
    if len(words) < k:
        return set()
    return {" ".join(words[i:i + k]) for i in range(len(words) - k + 1)}


def docs_corpus_shingles(root: Path, k: int = SHINGLE_K) -> set[str]:
    """Union of shingles over the whole `docs/` wiki — the authoritative project-fact corpus."""
    corpus: set[str] = set()
    docs = root / "docs"
    if not docs.is_dir():
        return corpus
    for md in sorted(docs.rglob("*.md")):
        try:
            corpus |= shingles(md.read_text(encoding="utf-8"), k)
        except OSError:
            continue
    return corpus


def containment(note_text: str, docs_sh: set[str], k: int = SHINGLE_K) -> float:
    """Fraction of the note's shingles already present in `docs/` (0.0..1.0). 0.0 if the note is too
    short to shingle (no measurable duplication)."""
    note_sh = shingles(_strip_frontmatter(note_text), k)
    if not note_sh:
        return 0.0
    return len(note_sh & docs_sh) / len(note_sh)


def band_of(score: float) -> str:
    return "HIGH" if score >= BAND_HIGH else ("LOW" if score < BAND_LOW else "MID")


# ── measurement ────────────────────────────────────────────────────────────────
def _note_type(text: str) -> str:
    m = re.search(r"^\s*type:\s*(\w+)", text, re.MULTILINE)
    return m.group(1) if m else "?"


def measure(memdir: Path, docs_sh: set[str], k: int = SHINGLE_K) -> list[dict]:
    """Per-note {name, type, lines, score, band}, sorted worst-duplicator first. Excludes MEMORY.md
    (the index itself — measured separately as the fixed per-session cost)."""
    rows: list[dict] = []
    for note in sorted(memdir.glob("*.md")):
        if note.name == "MEMORY.md":
            continue
        try:
            text = note.read_text(encoding="utf-8")
        except OSError:
            continue
        score = containment(text, docs_sh, k)
        rows.append({
            "name": note.name,
            "type": _note_type(text),
            "lines": text.count("\n") + 1,
            "score": round(score, 3),
            "band": band_of(score),
        })
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows


def memory_index_tokens(memdir: Path) -> int:
    """Estimated token footprint of MEMORY.md — the cost FIXED at every SessionStart (model-free ~4ch/tok)."""
    try:
        return len((memdir / "MEMORY.md").read_text(encoding="utf-8")) // _CHARS_PER_TOKEN
    except OSError:
        return 0


# ── bounded readout (for `meta metrics --overlap`; never dumps the raw corpus) ─
def summarize(root: Path, *, explicit: str | None = None, k: int = SHINGLE_K) -> list[str]:
    """≤~6 lines: the fixed cost, the by-type/by-band tallies, and the worst project-fact duplicators.
    Absent note-store → a single honest line (portable: clean clone has no auto-memory)."""
    memdir = find_memdir(root, explicit)
    if memdir is None:
        return ["SOLAPAMIENTO  note-store de auto-memoria ausente en esta máquina "
                "(fuera del árbol git; nada que medir — esperado en clon limpio/CI)"]

    docs_sh = docs_corpus_shingles(root, k)
    rows = measure(memdir, docs_sh, k)
    idx_tok = memory_index_tokens(memdir)
    by_type: dict[str, int] = {}
    for r in rows:
        by_type[r["type"]] = by_type.get(r["type"], 0) + 1
    high = [r for r in rows if r["band"] == "HIGH"]
    # Candidates for pointer-degrade: `project`-typed notes (narrate facts `docs/` owns), surfaced by
    # descending literal overlap. The metric SURFACES; the single-source RULE decides. Low scores here
    # mean the notes PARAPHRASE docs/ rather than copy it — the risk is semantic, not copy-paste.
    candidates = [r for r in rows if r["type"] == "project"][:4]

    lines = [
        f"SOLAPAMIENTO  {len(rows)} note(s) · "
        + " · ".join(f"{t}×{n}" for t, n in sorted(by_type.items()))
        + f" · MEMORY.md {idx_tok} tok"
        + (f" > presupuesto {MEMORY_INDEX_BUDGET_TOKENS}" if idx_tok > MEMORY_INDEX_BUDGET_TOKENS
           else f"/{MEMORY_INDEX_BUDGET_TOKENS} (ok)"),
        f"  containment literal vs docs/ (k={k}): {len(high)} alto(s) · "
        f"{sum(1 for r in rows if r['band']=='MID')} medio(s) · "
        f"{sum(1 for r in rows if r['band']=='LOW')} bajo(s)  "
        f"[bajo = paráfrasis, no copia → riesgo semántico, no copy-paste]",
        f"  project (autoridad = docs/; candidatos a puntero, por solapamiento ↓): "
        + (" · ".join(f"{r['name']}={r['score']}" for r in candidates) if candidates else "ninguno"),
    ]
    return lines
