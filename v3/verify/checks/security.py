#!/usr/bin/env python3
"""security — a heritable secret/supply-chain scan (ADR-017 Fase 3), PORTED from v2's
`verify/checks/security_scan.py` over v3's OWN shipped substrate instead of v2's.

    python3 -m v3.verify.checks.security

AI-written code ships secrets and hallucinated/vulnerable deps at meaningful rates (ADR-017 §2
honest-limits), so a green functional gate is necessary but NOT sufficient — this adds a
deterministic, network-free, stdlib-only scan (I-3; no tech named, ADR-012).

GREEN side — the shipped substrate (`v3`, `seed`, `.claude/hooks`, `.claude/agents`; v2 scanned its
own platform package in that first position instead of `v3` — the platform package is the only
re-pointed element, the rest of the subject is unchanged) scans CLEAN: no hardcoded credential
matches. A real secret committed to the substrate turns this RED.

RED side — EMBEDDED (`witness=Witness("fixture", ...)`, see `Witness.is_embedded`), asserted INSIDE
this same run, exactly as v2's `security_scan.py` did: scanning the planted-secret fixture
(`tests/fixtures/security/planted_secrets.txt`, fake AWS example key + PEM header — never a real
credential) MUST fire. If it comes back clean the scanner is decorative.

IF THE FIXTURE IS MISSING AT RUN TIME: unlike v2 (which reports "N/A, SAFE-7" and stays green — the
quiet hole `v3.verify.registry`'s docstring names as refusal #3), this run goes RED. Registration
already refuses a `fixture` witness whose path is not in the tree, so reaching this branch means the
tree changed under a live process; the ported behaviour here matches `v3.verify.checks.quality`'s own
fixture-missing branch, not v2's silent SAFE-7 pass.

The patterns match credential FORMATS, not their own source (a regex never matches itself), so this
scanner file is itself clean on the GREEN side.

ALSO PORTED, unchanged in subject (factories, never the platform): the H-4 anti-slopsquatting check —
every dependency declared in an emitted `factories/*/{build,products}/**` build file must be in the
committed allowlist (`docs/reference/dep-allowlist.yml`). Missing allowlist -> reported N/A (SAFE-7
still applies here: this is NOT the registered witness, just an additional real-world check ported
unchanged, so a missing allowlist is honestly nothing-to-check rather than a disarmed tooth).
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from math import log2
from pathlib import Path

from ...kernel.report import Verdict

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root

# Shipped substrate dirs the GREEN side must keep credential-free (disjoint from the RED fixture).
# Re-pointed from v2's own platform package to v3's; the rest is unchanged.
_GREEN_DIRS = ("v3", "seed", ".claude/hooks", ".claude/agents")
_FIXTURE_REL = "tests/fixtures/security/planted_secrets.txt"
_SCAN_EXT = {".py", ".md", ".json", ".yml", ".yaml", ".sh", ".txt", ".kt", ".ts"}

#: (label, compiled pattern) — credential FORMATS, network-free. Transcribed verbatim from v2.
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

# H-4 entropy detector: a QUOTED run of >=32 base64-charset characters with Shannon entropy >= 4.8
# bits/char is a probable credential even when no known format matches. Pure-hex runs are EXEMPT
# (git/sha digests saturate the tree — an honest, DECLARED blind spot, not a silent one).
_ENTROPY_CANDIDATE = re.compile(r"['\"]([A-Za-z0-9+/=_-]{32,})['\"]")
_HEX_ONLY = re.compile(r"^[0-9a-fA-F]+$")
_ENTROPY_MIN_BITS = 4.8


def _shannon_bits(s: str) -> float:
    """Shannon entropy of `s` in bits per character (stdlib only)."""
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
                hits.append("high-entropy-string@L" + str(i))
                break  # one entropy hit per line is enough signal
    return hits


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


def scan_paths(root: Path, rels: list[str]) -> dict[str, list[str]]:
    """Scan each existing file under `rels`; return {relpath: [hits]} for files with hits."""
    out: dict[str, list[str]] = {}
    for rel in rels:
        p = root / rel
        if not p.is_file() or p.suffix not in _SCAN_EXT:
            continue
        try:
            hits = scan_text(p.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if hits:
            out[rel] = hits
    return out


# -- H-4 anti-slopsquatting: declared deps subset-of a committed allowlist (network-free) -----------
_ALLOWLIST_REL = "docs/reference/dep-allowlist.yml"
_GRADLE_DEP = re.compile(r'\b(?:implementation|api)\("([^":]+:[^":]+)(?::[^"]*)?"\)')


def declared_deps(root: Path) -> dict[str, set[str]]:
    """{ecosystem: {dep}} declared across every emitted build file under factories/*/{build,products}.
    Subject unchanged from v2: factories are a product, not the platform, so nothing to re-point."""
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
                d = json.loads(p.read_text(encoding="utf-8", errors="replace"))
            except json.JSONDecodeError:
                continue
            for k in ("dependencies", "devDependencies"):
                out["npm"].update((d.get(k) or {}).keys())
    return out


def dep_problems(root: Path) -> list[str]:
    """Every declared dep NOT in the allowlist. Missing allowlist -> no problems (reported N/A by the
    caller separately — never silently folded into a green claim about deps that were never checked)."""
    allowlist_path = root / _ALLOWLIST_REL
    if not allowlist_path.exists():
        return []
    import yaml
    allow = yaml.safe_load(allowlist_path.read_text(encoding="utf-8")) or {}
    probs: list[str] = []
    for eco, deps in sorted(declared_deps(root).items()):
        allowed = set(allow.get(eco) or [])
        for d in sorted(deps - allowed):
            probs.append(f"{eco}: '{d}' declared but OUTSIDE {_ALLOWLIST_REL} — a hallucinated "
                         f"package? verify it in the real registry and add it DELIBERATELY (own commit)")
    return probs


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-security", 2, f"takes no arguments; got {argv!r}").emit()

    # 1. GREEN side — the shipped substrate must be credential-free.
    found = scan_paths(_ROOT, _walk(_ROOT, _GREEN_DIRS))
    if found:
        failures = tuple(f"{rel}: {', '.join(hits)}" for rel, hits in sorted(found.items()))
        return Verdict("v3-security", 1,
                       f"{len(found)} file(s) with hardcoded credential(s) in the substrate",
                       failures=failures,
                       next_action="remove the secret from code (env/secret-store); never commit "
                                   "one (ADR-017 §4)").emit()

    # 2. RED side (embedded, fixture witness) — the scanner MUST fire on the planted fixture.
    fixture = _ROOT / _FIXTURE_REL
    if not fixture.exists():
        return Verdict("v3-security", 1,
                       f"{_FIXTURE_REL} is not in the tree — the red witness is missing").emit()
    hits = scan_text(fixture.read_text(encoding="utf-8", errors="replace"))
    if not hits:
        return Verdict("v3-security", 1,
                       f"GATE DECORATIVO: the scanner did NOT flag the fixture {_FIXTURE_REL} — no "
                       f"teeth").emit()
    labels = sorted({h.split("@")[0] for h in hits})

    # 3. anti-slopsquatting — every declared dep (factories, unchanged subject) must be allowlisted.
    deps = dep_problems(_ROOT)
    if deps:
        return Verdict("v3-security", 1, f"{len(deps)} declared dependency/ies outside the allowlist "
                       f"(anti-slopsquatting, H-4)", failures=tuple(deps[:20])).emit()
    dep_note = ("allowlist N/A (no docs/reference/dep-allowlist.yml)"
                if not (_ROOT / _ALLOWLIST_REL).exists()
                else f"deps subset-of allowlist ({sum(len(v) for v in declared_deps(_ROOT).values())} declared)")

    nfiles = len(_walk(_ROOT, _GREEN_DIRS))
    return Verdict("v3-security", 0,
                   f"{nfiles} file(s) scanned under {'/'.join(_GREEN_DIRS)}, 0 credentials; red "
                   f"witness alive: {_FIXTURE_REL} -> {len(hits)} hit(s) [{', '.join(labels)}]; "
                   f"{dep_note}").emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
