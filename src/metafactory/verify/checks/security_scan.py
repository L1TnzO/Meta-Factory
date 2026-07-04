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

#: (label, compiled pattern) — credential FORMATS, network-free. Expanded 2026-07-04 (H-4,
#: COLUMN-MAINT): the standard low-false-positive corpus subset, 5 → 14 formats.
_PATTERNS = [
    ("aws-access-key-id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private-key-block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("generic-secret-assign",
     re.compile(r"(?i)(?:password|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*"
                r"['\"][^'\"\s]{12,}['\"]")),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("openai-key", re.compile(r"\bsk-(?:proj|live)-[A-Za-z0-9_-]{20,}\b")),
    ("stripe-key", re.compile(r"\b[rs]k_live_[A-Za-z0-9]{20,}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("gitlab-pat", re.compile(r"\bglpat-[A-Za-z0-9_-]{20}\b")),
    ("npm-token", re.compile(r"\bnpm_[A-Za-z0-9]{36}\b")),
    ("pypi-token", re.compile(r"\bpypi-AgEIcHlwaS5vcmc[A-Za-z0-9_-]{20,}\b")),
    ("sendgrid-key", re.compile(r"\bSG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}\b")),
    ("jwt-token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{6,}\b")),
]

# H-4 entropy detector: a QUOTED run of ≥32 base64-charset characters with Shannon entropy ≥ 4.8
# bits/char is a probable credential even when no known format matches. Pure-hex runs are EXEMPT
# (git/sha digests saturate the tree — an honest, DECLARED blind spot, not a silent one).
_ENTROPY_CANDIDATE = re.compile(r"['\"]([A-Za-z0-9+/=_-]{32,})['\"]")
_HEX_ONLY = re.compile(r"^[0-9a-fA-F]+$")
_ENTROPY_MIN_BITS = 4.8


def _shannon_bits(s: str) -> float:
    """Shannon entropy of `s` in bits per character (stdlib only)."""
    from collections import Counter
    from math import log2
    n = len(s)
    return -sum((c / n) * log2(c / n) for c in Counter(s).values()) if n else 0.0


def scan_text(text: str) -> list[str]:
    """Every credential format found in `text` (label@line), plus high-entropy quoted strings."""
    hits: list[str] = []
    for i, line in enumerate(text.splitlines(), 1):
        for label, pat in _PATTERNS:
            if pat.search(line):
                hits.append(f"{label}@L{i}")
        for m in _ENTROPY_CANDIDATE.finditer(line):
            s = m.group(1)
            if not _HEX_ONLY.match(s) and _shannon_bits(s) >= _ENTROPY_MIN_BITS:
                hits.append(f"high-entropy-string@L{i}")
                break  # one entropy hit per line is enough signal
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


# ── H-4 anti-slopsquatting: declared deps ⊆ committed allowlist (network-free) ───────────────────────
_ALLOWLIST = "docs/reference/dep-allowlist.yml"
_GRADLE_DEP = re.compile(r'\b(?:implementation|api)\("([^":]+:[^":]+)(?::[^"]*)?"\)')


def declared_deps(root: Path) -> dict[str, set[str]]:
    """{ecosystem: {dep}} declared across every emitted build file under factories/*/{build,products}.
    gradle: `implementation/api("group:artifact[:version]")` → group:artifact. npm: dependencies +
    devDependencies keys of any non-node_modules package.json."""
    import json as _json
    out: dict[str, set[str]] = {"gradle": set(), "npm": set()}
    for pat in ("factories/*/build/**/build.gradle.kts", "factories/*/products/**/build.gradle.kts"):
        for p in root.glob(pat):
            for m in _GRADLE_DEP.finditer(p.read_text(encoding="utf-8", errors="replace")):
                out["gradle"].add(m.group(1))
    for pat in ("factories/*/build/**/package.json", "factories/*/products/**/package.json"):
        for p in root.glob(pat):
            if "node_modules" in p.parts:
                continue
            try:
                d = _json.loads(p.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                continue
            for k in ("dependencies", "devDependencies"):
                out["npm"].update((d.get(k) or {}).keys())
    return out


def dep_problems(root: Path) -> list[str]:
    """Every declared dep NOT in the allowlist (the slopsquatting tooth). Missing allowlist -> N/A
    (reported by the caller, never silently green)."""
    al = root / _ALLOWLIST
    if not al.exists():
        return []
    import yaml as _yaml
    allow = _yaml.safe_load(al.read_text(encoding="utf-8")) or {}
    probs: list[str] = []
    for eco, deps in sorted(declared_deps(root).items()):
        allowed = set(allow.get(eco) or [])
        for d in sorted(deps - allowed):
            probs.append(f"{eco}: '{d}' declarada pero FUERA de {_ALLOWLIST} — ¿paquete alucinado? "
                         f"verificá en el registry real y agregala DELIBERADAMENTE (commit propio)")
    return probs


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

    # H-4 — anti-slopsquatting: every declared dep must be in the committed allowlist.
    deps = dep_problems(root)
    if deps:
        print("SECURITY_SCAN ROJO — dependencia(s) fuera de la allowlist (anti-slopsquatting, H-4):")
        for p in deps[:20]:
            print(f"  ✗ {p}")
        return 1
    dep_note = ("allowlist N/A (no está docs/reference/dep-allowlist.yml — no fingido, SAFE-7)"
                if not (root / _ALLOWLIST).exists()
                else f"deps ⊆ allowlist ({sum(len(v) for v in declared_deps(root).values())} declaradas)")

    nfiles = len(_walk(root, _GREEN_DIRS))
    print(f"OK security_scan: sustrato limpio ({nfiles} archivos, 0 credenciales); diente RED vivo: "
          f"{tooth}; {dep_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
