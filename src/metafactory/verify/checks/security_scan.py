"""security_scan — a heritable secret/supply-chain gate KIND (ADR-017 §4, DELEGATION-HARNESS Fase 3).

Generalizes what FSK already gates at product level (s4 supply-chain: hardcoded secrets, vulnerable deps) into
a reusable SUBSTRATE kind, dogfooded on our own tree. AI-written code ships secrets and hallucinated/vulnerable
deps at meaningful rates (ADR-017 §2 honest-limits), so a green functional gate is necessary but NOT sufficient
— this adds a deterministic, network-free, stdlib-only scan (I-3; no tech named, ADR-012).

Two-sided, like `quality_gate` / `pbt_gate`:
  GREEN side — the shipped substrate (`src/metafactory`, `seed`, `.claude/hooks`, `.claude/agents`) scans CLEAN:
               no hardcoded credential matches. A real secret committed to the substrate turns this RED.
  RED side   — scanning the planted-secret fixture (`tests/fixtures/security/planted_secrets.txt`, fake AWS
               example key + PEM header — never a real credential) MUST fire. If it comes back clean the
               scanner is decorative → this check FAILS.

The patterns match credential FORMATS, not their own source (a regex never matches itself), so the scanner
file is itself clean on the GREEN side.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Shipped substrate dirs the GREEN side must keep credential-free (disjoint from the RED fixture).
_GREEN_DIRS = ("src/metafactory", "seed", ".claude/hooks", ".claude/agents")
_FIXTURE = "tests/fixtures/security/planted_secrets.txt"
_SCAN_EXT = {".py", ".md", ".json", ".yml", ".yaml", ".sh", ".txt", ".kt", ".ts"}

#: (label, compiled pattern) — credential FORMATS, network-free.
_PATTERNS = [
    ("aws-access-key-id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private-key-block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("generic-secret-assign",
     re.compile(r"(?i)(?:password|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*"
                r"['\"][^'\"\s]{12,}['\"]")),
]


def scan_text(text: str) -> list[str]:
    """Every credential format found in `text` (label@line)."""
    hits: list[str] = []
    for i, line in enumerate(text.splitlines(), 1):
        for label, pat in _PATTERNS:
            if pat.search(line):
                hits.append(f"{label}@L{i}")
    return hits


def scan_paths(root: Path, rels: list[str]) -> dict[str, list[str]]:
    """Scan each existing file under `rels`; return {relpath: [hits]} for files with hits."""
    out: dict[str, list[str]] = {}
    for rel in rels:
        p = root / rel
        if not p.is_file() or p.suffix not in _SCAN_EXT:
            continue
        try:
            hits = scan_text(p.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        if hits:
            out[rel] = hits
    return out


def _walk(root: Path, dirs: tuple[str, ...]) -> list[str]:
    rels: list[str] = []
    for d in dirs:
        base = root / d
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file() and p.suffix in _SCAN_EXT and "__pycache__" not in p.parts:
                rels.append(p.relative_to(root).as_posix())
    return sorted(rels)


def main(argv: list[str]) -> int:
    root = Path(argv[0]).resolve() if argv else Path.cwd()

    # GREEN side — the shipped substrate must be credential-free.
    found = scan_paths(root, _walk(root, _GREEN_DIRS))
    if found:
        print("SECURITY_SCAN ROJO — credencial(es) hardcodeada(s) en el sustrato:")
        for rel, hits in sorted(found.items()):
            print(f"  ✗ {rel}: {', '.join(hits)}")
        print("  -> sacá el secreto del código (a env/secret-store); nunca se commitea (ADR-017 §4).")
        return 1

    # RED side (two-sided tooth) — the scanner MUST fire on the planted fixture.
    fx = root / _FIXTURE
    if not fx.exists():
        tooth = f"N/A (no está {_FIXTURE} — no fingido, SAFE-7)"
    else:
        hits = scan_text(fx.read_text(encoding="utf-8", errors="replace"))
        if not hits:
            print(f"SECURITY_SCAN DECORATIVO — el scanner NO marcó el fixture {_FIXTURE} → sin dientes")
            return 1
        tooth = f"{_FIXTURE} → {len(hits)} hit(s) [{', '.join(sorted(set(h.split('@')[0] for h in hits)))}]"

    nfiles = len(_walk(root, _GREEN_DIRS))
    print(f"OK security_scan: sustrato limpio ({nfiles} archivos, 0 credenciales); diente RED vivo: {tooth}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
